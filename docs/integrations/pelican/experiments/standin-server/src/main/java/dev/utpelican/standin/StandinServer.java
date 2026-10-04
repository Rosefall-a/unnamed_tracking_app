package dev.utpelican.standin;

import net.kyori.adventure.nbt.BinaryTag;
import net.kyori.adventure.nbt.BinaryTagIO;
import net.kyori.adventure.nbt.CompoundBinaryTag;
import net.kyori.adventure.nbt.DoubleBinaryTag;
import net.kyori.adventure.nbt.FloatBinaryTag;
import net.kyori.adventure.nbt.ListBinaryTag;
import net.minestom.server.Auth;
import net.minestom.server.MinecraftServer;
import net.minestom.server.coordinate.Pos;
import net.minestom.server.entity.GameMode;
import net.minestom.server.entity.Player;
import net.minestom.server.event.GlobalEventHandler;
import net.minestom.server.event.player.AsyncPlayerConfigurationEvent;
import net.minestom.server.event.player.PlayerDisconnectEvent;
import net.minestom.server.event.player.PlayerSpawnEvent;
import net.minestom.server.instance.InstanceContainer;
import net.minestom.server.instance.Weather;
import net.minestom.server.instance.anvil.AnvilLoader;
import net.minestom.server.instance.block.Block;
import net.minestom.server.tag.Tag;
import net.minestom.server.world.DimensionType;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Disposable Minecraft Java Edition (26.1.2 protocol) stand-in used by the Pelican discovery
 * experiments while the Mojang/PaperMC download hosts are unavailable.
 *
 * <p>It deliberately mimics the observable contract a Pelican Minecraft egg relies on:
 * vanilla-format log lines (readiness, join/leave, list), the {@code stop}/{@code save-all}/
 * {@code save-off}/{@code save-on} console commands, {@code server.properties}, and an Anvil world
 * with {@code level.dat} and per-player data in the 26.x world layout. It is NOT a vanilla
 * server: terrain generation, mobs and gameplay are intentionally trivial.
 */
public final class StandinServer {
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("HH:mm:ss");
    private static final Tag<BinaryTag> DATA = Tag.NBT("Data");

    private static InstanceContainer world;
    private static Path worldPath;
    private static Properties properties;
    private static volatile boolean autosave = true;
    private static long seed;
    private static int spawnX;
    private static int spawnY;
    private static int spawnZ;

    private StandinServer() {
    }

    public static void main(String[] args) throws Exception {
        final long started = System.nanoTime();
        properties = loadProperties(Path.of("server.properties"));
        final String levelName = properties.getProperty("level-name", "world");
        final int port = Integer.parseInt(properties.getProperty("server-port", "25565"));
        final String ip = properties.getProperty("server-ip", "");
        worldPath = Path.of(levelName);

        log("Starting minecraft server version " + MinecraftServer.VERSION_NAME + " (UT stand-in)");
        log("Loading properties");
        log("Default game type: SURVIVAL");
        log("Starting Minecraft server on " + (ip.isEmpty() ? "*" : ip) + ":" + port);

        final MinecraftServer server = MinecraftServer.init(new Auth.Offline());
        log("Preparing level \"" + levelName + "\"");
        Files.createDirectories(worldPath.resolve("players").resolve("data"));
        validateLevelDat(worldPath.resolve("level.dat"));

        world = MinecraftServer.getInstanceManager().createInstanceContainer(
                DimensionType.OVERWORLD, new AnvilLoader(worldPath, DimensionType.OVERWORLD.key()));
        initialiseLevelData(levelName);
        world.setGenerator(unit -> {
            final var start = unit.absoluteStart();
            final var size = unit.size();
            for (int dx = 0; dx < size.blockX(); dx++) {
                for (int dz = 0; dz < size.blockZ(); dz++) {
                    final int x = start.blockX() + dx;
                    final int z = start.blockZ() + dz;
                    final int h = heightAt(x, z);
                    for (int y = Math.max(start.blockY(), -64); y < Math.min(start.blockY() + size.blockY(), Math.max(h, 62) + 1); y++) {
                        final Block block;
                        if (y == -64) {
                            block = Block.BEDROCK;
                        } else if (y > h) {
                            block = Block.WATER;
                        } else if (y == h) {
                            block = h < 63 ? Block.SAND : (h > 92 ? Block.SNOW_BLOCK : Block.GRASS_BLOCK);
                        } else if (y > h - 4) {
                            block = h < 63 ? Block.SAND : Block.DIRT;
                        } else {
                            block = Block.STONE;
                        }
                        unit.modifier().setBlock(x, y, z, block);
                    }
                }
            }
        });

        final GlobalEventHandler events = MinecraftServer.getGlobalEventHandler();
        events.addListener(AsyncPlayerConfigurationEvent.class, event -> {
            final Player player = event.getPlayer();
            event.setSpawningInstance(world);
            player.setRespawnPoint(loadPlayerPosition(player.getUuid()));
            player.setGameMode(GameMode.CREATIVE);
        });
        events.addListener(PlayerSpawnEvent.class, event -> {
            if (!event.isFirstSpawn()) {
                return;
            }
            final Player player = event.getPlayer();
            final Pos pos = player.getPosition();
            log(player.getUsername() + "[" + player.getPlayerConnection().getRemoteAddress()
                    + "] logged in with entity id " + player.getEntityId()
                    + String.format(" at (%.1f, %.1f, %.1f)", pos.x(), pos.y(), pos.z()));
            log(player.getUsername() + " joined the game");
        });
        events.addListener(PlayerDisconnectEvent.class, event -> {
            final Player player = event.getPlayer();
            savePlayer(player);
            log(player.getUsername() + " lost connection: Disconnected");
            log(player.getUsername() + " left the game");
        });

        if (System.getenv("UT_STANDIN_NEVER_READY") != null) {
            // Failure-mode hook: bind the port but never print the readiness line.
            server.start(ip.isEmpty() ? "0.0.0.0" : ip, port);
            log("Readiness suppressed by UT_STANDIN_NEVER_READY");
        } else {
            server.start(ip.isEmpty() ? "0.0.0.0" : ip, port);
            // Pre-load the spawn area before announcing readiness, like vanilla.
            for (int cx = -2; cx <= 2; cx++) {
                for (int cz = -2; cz <= 2; cz++) {
                    world.loadChunk(cx, cz).join();
                }
            }
            final double seconds = (System.nanoTime() - started) / 1_000_000_000.0;
            log(String.format("Done (%.3fs)! For help, type \"help\"", seconds));
        }

        MinecraftServer.getSchedulerManager().buildTask(() -> {
            if (autosave) {
                saveAll(false);
            }
        }).repeat(java.time.Duration.ofMinutes(5)).delay(java.time.Duration.ofMinutes(5)).schedule();

        final Thread console = new Thread(StandinServer::readConsole, "Server console handler");
        console.setDaemon(true);
        console.start();
    }

    private static void readConsole() {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                final String command = line.trim();
                if (!command.isEmpty()) {
                    MinecraftServer.getSchedulerManager().scheduleNextTick(() -> handle(command));
                }
            }
        } catch (IOException e) {
            log("Console closed: " + e.getMessage());
        }
    }

    private static void handle(String command) {
        final String[] parts = command.startsWith("/") ? command.substring(1).split("\\s+") : command.split("\\s+");
        switch (parts[0]) {
            case "stop" -> stop();
            case "list" -> {
                final var players = MinecraftServer.getConnectionManager().getOnlinePlayers();
                log("There are " + players.size() + " of a max of " + properties.getProperty("max-players", "20")
                        + " players online: " + players.stream().map(Player::getUsername).collect(Collectors.joining(", ")));
            }
            case "save-all" -> saveAll(true);
            case "save-off" -> {
                autosave = false;
                log("Automatic saving is now disabled");
            }
            case "save-on" -> {
                autosave = true;
                log("Automatic saving is now enabled");
            }
            case "seed" -> log("Seed: [" + seed + "]");
            case "time" -> log("The time is " + world.getTime());
            case "weather" -> {
                if (parts.length > 1 && !parts[1].equals("query")) {
                    world.setWeather(parts[1].equals("clear") ? Weather.CLEAR : Weather.RAIN);
                    log("Changing the weather to " + parts[1]);
                } else {
                    log("Weather: " + (world.getWeather().rainLevel() > 0 ? "rain" : "clear"));
                }
            }
            case "data" -> {
                // data get entity <player> Pos
                final Player player = parts.length > 3 ? MinecraftServer.getConnectionManager().findOnlinePlayer(parts[3]) : null;
                if (player == null) {
                    log("No entity was found");
                } else {
                    final Pos p = player.getPosition();
                    log(player.getUsername() + " has the following entity data: ["
                            + p.x() + "d, " + p.y() + "d, " + p.z() + "d]");
                }
            }
            case "tp" -> {
                final Player player = parts.length > 4 ? MinecraftServer.getConnectionManager().findOnlinePlayer(parts[1]) : null;
                if (player == null) {
                    log("No entity was found");
                } else {
                    final Pos target = new Pos(Double.parseDouble(parts[2]), Double.parseDouble(parts[3]), Double.parseDouble(parts[4]));
                    player.teleport(target).join();
                    log("Teleported " + player.getUsername() + " to " + target.x() + ", " + target.y() + ", " + target.z());
                }
            }
            case "ut-marker" -> buildMarker(parts.length > 1 ? parts[1] : "minecraft:gold_block");
            case "ut-crash" -> {
                // Failure-mode hook: die without saving, like a JVM crash.
                log("Simulated crash requested");
                Runtime.getRuntime().halt(137);
            }
            case "help" -> log("stop, list, save-all, save-off, save-on, seed, time, weather, data get entity <p> Pos, tp <p> x y z");
            default -> log("Unknown or incomplete command, see below for error");
        }
    }

    /** Builds an unmistakable marker: a 12-high pillar at spawn and a 9x9 pad at (16, *, 16). */
    private static void buildMarker(String blockKey) {
        final Block block = Block.fromKey(blockKey);
        if (block == null) {
            log("Unknown block " + blockKey);
            return;
        }
        world.loadChunk(0, 0).join();
        world.loadChunk(1, 1).join();
        final int base = surfaceAt(0, 0) + 1;
        for (int y = base; y < base + 12; y++) {
            world.setBlock(0, y, 0, block);
        }
        final int padY = surfaceAt(16, 16) + 1;
        for (int x = 12; x <= 20; x++) {
            for (int z = 12; z <= 20; z++) {
                world.setBlock(x, padY, z, block);
            }
        }
        log("Marker " + blockKey + " built at pillar (0," + base + ",0) and pad (12..20," + padY + ",12..20)");
    }

    private static int surfaceAt(int x, int z) {
        for (int y = 319; y > -64; y--) {
            final Block b = world.getBlock(x, y, z);
            if (!b.isAir() && !b.compare(Block.WATER)) {
                return y;
            }
        }
        return -64;
    }

    private static int heightAt(int x, int z) {
        final double s = (seed % 1000) / 100.0;
        final double h = 70
                + 9 * Math.sin((x + s * 37) / 23.0) * Math.cos((z - s * 11) / 29.0)
                + 5 * Math.sin((x + z + s * 53) / 11.0)
                + 3 * Math.cos((x - z) / 7.0);
        return (int) Math.round(h);
    }

    private static void saveAll(boolean announce) {
        if (announce) {
            log("Saving the game (this may take a moment!)");
        }
        persistLevelData();
        for (Player player : MinecraftServer.getConnectionManager().getOnlinePlayers()) {
            savePlayer(player);
        }
        world.saveInstance().join();
        world.saveChunksToStorage().join();
        if (announce) {
            log("Saved the game");
        }
    }

    private static void stop() {
        log("Stopping the server");
        log("Stopping server");
        log("Saving players");
        for (Player player : MinecraftServer.getConnectionManager().getOnlinePlayers()) {
            savePlayer(player);
            player.kick("Server closed");
        }
        log("Saving worlds");
        persistLevelData();
        world.saveInstance().join();
        world.saveChunksToStorage().join();
        log("ThreadedAnvilChunkStorage: All dimensions are saved");
        MinecraftServer.stopCleanly();
        System.exit(0);
    }

    private static void validateLevelDat(Path levelDat) {
        if (!Files.exists(levelDat)) {
            return;
        }
        try (InputStream in = Files.newInputStream(levelDat)) {
            final CompoundBinaryTag root = BinaryTagIO.reader().read(in, BinaryTagIO.Compression.GZIP);
            final int dataVersion = root.getCompound("Data").getInt("DataVersion", 0);
            if (dataVersion > MinecraftServer.DATA_VERSION) {
                log("ERROR", "Failed to load level \"" + levelDat.getParent() + "\": world was saved with a newer version "
                        + "(DataVersion " + dataVersion + " > " + MinecraftServer.DATA_VERSION + ")");
                System.exit(1);
            }
        } catch (IOException | RuntimeException e) {
            log("ERROR", "Failed to load level.dat: " + e);
            System.exit(1);
        }
    }

    private static void initialiseLevelData(String levelName) {
        CompoundBinaryTag data = world.getTag(DATA) instanceof CompoundBinaryTag existing ? existing : null;
        if (data == null) {
            final long newSeed = System.getenv("UT_STANDIN_SEED") != null
                    ? Long.parseLong(System.getenv("UT_STANDIN_SEED")) : new java.util.Random().nextLong();
            log("WARN", "No existing world data, creating new world");
            data = CompoundBinaryTag.builder()
                    .putString("LevelName", System.getenv().getOrDefault("UT_STANDIN_LEVEL_NAME", levelName))
                    .putInt("DataVersion", MinecraftServer.DATA_VERSION)
                    .put("Version", CompoundBinaryTag.builder()
                            .putString("Name", MinecraftServer.VERSION_NAME)
                            .putInt("Id", MinecraftServer.DATA_VERSION)
                            .putString("Series", "main").build())
                    .put("WorldGenSettings", CompoundBinaryTag.builder().putLong("seed", newSeed).build())
                    .putInt("SpawnX", 0).putInt("SpawnY", heightAt(0, 0) + 1).putInt("SpawnZ", 0)
                    .putLong("Time", 0).putLong("DayTime", 1000)
                    .putByte("raining", (byte) 0)
                    .putString("UTStandin", "1")
                    .build();
        }
        seed = data.getCompound("WorldGenSettings").getLong("seed");
        spawnX = data.getInt("SpawnX");
        spawnY = data.getInt("SpawnY");
        spawnZ = data.getInt("SpawnZ");
        world.setTag(DATA, data);
        world.setTime(data.getLong("DayTime"));
        world.setWeather(data.getByte("raining") != 0 ? Weather.RAIN : Weather.CLEAR);
        log("Level \"" + data.getString("LevelName") + "\" seed " + seed + " spawn " + spawnX + "," + spawnY + "," + spawnZ);
    }

    private static void persistLevelData() {
        final CompoundBinaryTag data = (CompoundBinaryTag) world.getTag(DATA);
        world.setTag(DATA, data.putLong("DayTime", world.getTime())
                .putByte("raining", (byte) (world.getWeather().rainLevel() > 0 ? 1 : 0))
                .putLong("LastPlayed", System.currentTimeMillis()));
    }

    private static Pos loadPlayerPosition(UUID uuid) {
        final Path file = worldPath.resolve("players").resolve("data").resolve(uuid + ".dat");
        if (Files.exists(file)) {
            try (InputStream in = Files.newInputStream(file)) {
                final CompoundBinaryTag tag = BinaryTagIO.reader().read(in, BinaryTagIO.Compression.GZIP);
                final ListBinaryTag p = tag.getList("Pos");
                final ListBinaryTag r = tag.getList("Rotation");
                return new Pos(p.getDouble(0), p.getDouble(1), p.getDouble(2), r.getFloat(0), r.getFloat(1));
            } catch (IOException | RuntimeException e) {
                log("WARN", "Failed to load player data for " + uuid + ": " + e);
            }
        }
        return new Pos(spawnX + 0.5, spawnY, spawnZ + 0.5);
    }

    private static void savePlayer(Player player) {
        final Pos p = player.getPosition();
        final CompoundBinaryTag tag = CompoundBinaryTag.builder()
                .put("Pos", ListBinaryTag.from(java.util.List.of(DoubleBinaryTag.doubleBinaryTag(p.x()),
                        DoubleBinaryTag.doubleBinaryTag(p.y()), DoubleBinaryTag.doubleBinaryTag(p.z()))))
                .put("Rotation", ListBinaryTag.from(java.util.List.of(FloatBinaryTag.floatBinaryTag(p.yaw()),
                        FloatBinaryTag.floatBinaryTag(p.pitch()))))
                .putString("Dimension", "minecraft:overworld")
                .putInt("DataVersion", MinecraftServer.DATA_VERSION)
                .putString("LastKnownName", player.getUsername())
                .build();
        final Path dir = worldPath.resolve("players").resolve("data");
        final Path tmp = dir.resolve(player.getUuid() + ".dat_tmp");
        try {
            Files.createDirectories(dir);
            try (OutputStream out = Files.newOutputStream(tmp)) {
                BinaryTagIO.writer().writeNamed(Map.entry("", tag), out, BinaryTagIO.Compression.GZIP);
            }
            Files.move(tmp, dir.resolve(player.getUuid() + ".dat"), StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            log("WARN", "Failed to save player data for " + player.getUsername() + ": " + e);
        }
    }

    private static Properties loadProperties(Path path) throws IOException {
        final Properties props = new Properties();
        if (Files.exists(path)) {
            try (InputStream in = Files.newInputStream(path)) {
                props.load(in);
            }
        } else {
            props.setProperty("server-port", "25565");
            props.setProperty("server-ip", "");
            props.setProperty("level-name", "world");
            props.setProperty("max-players", "20");
            props.setProperty("motd", "Unnamed Tracking stand-in");
            try (OutputStream out = Files.newOutputStream(path)) {
                props.store(out, "Minecraft server properties");
            }
        }
        return props;
    }

    private static void log(String message) {
        log("INFO", message);
    }

    private static void log(String level, String message) {
        System.out.println("[" + LocalTime.now().format(TIME) + "] [Server thread/" + level + "]: " + message);
        System.out.flush();
    }
}
