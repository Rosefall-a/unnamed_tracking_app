package com.rosefall.tracker

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CollectionsBookmark
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.rosefall.tracker.network.ApiClient
import com.rosefall.tracker.network.ApiException
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

private const val APP_PREFERENCES = "tracking-app"
private const val SERVER_URL = "server-url"

@Composable
fun TrackingApp() {
    val context = LocalContext.current
    val preferences = remember { context.getSharedPreferences(APP_PREFERENCES, Context.MODE_PRIVATE) }
    val configuredDefault = remember {
        BuildConfig.DEFAULT_SERVER_URL.takeIf { it.isNotBlank() }?.let { runCatching { ServerUrl.normalize(it) }.getOrNull() }
    }
    var serverUrl by rememberSaveable {
        mutableStateOf(preferences.getString(SERVER_URL, null) ?: configuredDefault)
    }

    if (serverUrl == null) {
        ServerSetupScreen { value ->
            preferences.edit().putString(SERVER_URL, value).apply()
            serverUrl = value
        }
        return
    }

    val client = remember(serverUrl) { ApiClient(context.applicationContext, serverUrl!!) }
    SessionGate(
        client = client,
        onChangeServer = {
            preferences.edit().remove(SERVER_URL).apply()
            serverUrl = null
        },
    )
}

@Composable
private fun ServerSetupScreen(onConnected: (String) -> Unit) {
    var value by rememberSaveable { mutableStateOf("") }
    var error by rememberSaveable { mutableStateOf<String?>(null) }
    Box(Modifier.fillMaxSize().padding(horizontal = 24.dp), contentAlignment = Alignment.Center) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(28.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        ) {
            Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text("Connect your library", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Text(
                    "Enter the address of your tracking server. Include http:// for a local HTTP server or https:// for TLS.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedTextField(
                    value = value,
                    onValueChange = { value = it; error = null },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Server address") },
                    placeholder = { Text("http://192.168.1.20:5173") },
                    singleLine = true,
                    isError = error != null,
                    supportingText = error?.let { message -> { Text(message) } },
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = {
                        runCatching { ServerUrl.normalize(value) }
                            .onSuccess(onConnected)
                            .onFailure { error = it.message }
                    }),
                )
                Button(
                    onClick = {
                        runCatching { ServerUrl.normalize(value) }
                            .onSuccess(onConnected)
                            .onFailure { error = it.message }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Continue") }
                Text(
                    "Private network addresses without a scheme use HTTP; public names use HTTPS.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

private enum class SessionState { CHECKING, SIGNED_OUT, SIGNED_IN }

@Composable
private fun SessionGate(client: ApiClient, onChangeServer: () -> Unit) {
    var state by remember(client) { mutableStateOf(SessionState.CHECKING) }
    var user by remember(client) { mutableStateOf<JsonObject?>(null) }
    var connectionError by remember(client) { mutableStateOf<String?>(null) }

    suspend fun checkSession() {
        state = SessionState.CHECKING
        connectionError = null
        try {
            user = client.get("/api/auth/me") as? JsonObject
            state = SessionState.SIGNED_IN
        } catch (error: ApiException) {
            state = if (error.status == 401) SessionState.SIGNED_OUT else SessionState.CHECKING
            if (error.status != 401) connectionError = error.message
        } catch (error: Exception) {
            connectionError = error.message ?: "Could not connect to the server."
        }
    }

    LaunchedEffect(client) { checkSession() }

    when {
        connectionError != null -> ConnectionErrorScreen(
            message = connectionError!!,
            onRetry = { connectionError = null; state = SessionState.CHECKING },
            onChangeServer = onChangeServer,
            retry = { checkSession() },
        )
        state == SessionState.CHECKING -> LoadingScreen()
        state == SessionState.SIGNED_OUT -> LoginScreen(client, onSignedIn = { checkSession() }, onChangeServer)
        else -> MainScreen(
            client = client,
            user = user,
            onSignedOut = { state = SessionState.SIGNED_OUT; user = null },
            onChangeServer = onChangeServer,
        )
    }
}

@Composable
private fun LoadingScreen() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
}

@Composable
private fun ConnectionErrorScreen(
    message: String,
    onRetry: () -> Unit,
    onChangeServer: () -> Unit,
    retry: suspend () -> Unit,
) {
    val scope = rememberCoroutineScope()
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        Card(shape = RoundedCornerShape(24.dp)) {
            Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("Server unavailable", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick = { onRetry(); scope.launch { retry() } }, modifier = Modifier.fillMaxWidth()) {
                    Text("Try again")
                }
                OutlinedButton(onClick = onChangeServer, modifier = Modifier.fillMaxWidth()) { Text("Change server") }
            }
        }
    }
}

@Composable
private fun LoginScreen(client: ApiClient, onSignedIn: suspend () -> Unit, onChangeServer: () -> Unit) {
    var identifier by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    fun submit() {
        if (identifier.isBlank() || password.isBlank() || loading) return
        scope.launch {
            loading = true
            error = null
            try { client.login(identifier.trim(), password); onSignedIn() }
            catch (exception: Exception) { error = exception.message ?: "Sign in failed." }
            finally { loading = false }
        }
    }
    Box(Modifier.fillMaxSize().padding(horizontal = 24.dp), contentAlignment = Alignment.Center) {
        Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(28.dp)) {
            Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("Welcome back", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Text(client.baseUrl, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedTextField(identifier, { identifier = it }, Modifier.fillMaxWidth(), label = { Text("Username or email") }, singleLine = true)
                OutlinedTextField(
                    password,
                    { password = it },
                    Modifier.fillMaxWidth(),
                    label = { Text("Password") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = { submit() }),
                )
                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                Button(onClick = ::submit, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                    if (loading) CircularProgressIndicator(Modifier.height(20.dp)) else Text("Sign in")
                }
                TextButton(onClick = onChangeServer, modifier = Modifier.align(Alignment.CenterHorizontally)) { Text("Change server") }
            }
        }
    }
}

private data class Tab(val label: String, val icon: ImageVector)
private val tabs = listOf(Tab("Home", Icons.Default.Home), Tab("Games", Icons.Default.SportsEsports), Tab("More", Icons.Default.MoreHoriz))

@Composable
private fun MainScreen(client: ApiClient, user: JsonObject?, onSignedOut: () -> Unit, onChangeServer: () -> Unit) {
    var selectedTab by rememberSaveable { mutableIntStateOf(0) }
    var destination by remember { mutableStateOf<NativeDestination?>(null) }
    val scope = rememberCoroutineScope()
    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEachIndexed { index, tab ->
                    NavigationBarItem(
                        selected = selectedTab == index && destination == null,
                        onClick = { selectedTab = index; destination = null },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { padding ->
        if (destination != null) {
            NativeDataScreen(client, destination!!, padding, onBack = { destination = null })
        } else when (selectedTab) {
            0 -> HomeScreen(client, user, padding)
            1 -> GamesScreen(client, padding)
            else -> MoreScreen(
                padding,
                onOpen = { destination = it },
                onLogout = { scope.launch { client.logout(); onSignedOut() } },
                onChangeServer = onChangeServer,
            )
        }
    }
}

@Composable
private fun ScreenHeader(title: String, subtitle: String? = null, onRefresh: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            subtitle?.let { Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
        onRefresh?.let { IconButton(onClick = it) { Icon(Icons.Default.Refresh, "Refresh") } }
    }
}

@Composable
private fun HomeScreen(client: ApiClient, user: JsonObject?, padding: PaddingValues) {
    NativeDataContent(
        client = client,
        path = "/api/stats/overview",
        modifier = Modifier.padding(padding),
        header = {
            ScreenHeader(
                "Hello, ${user.string("username") ?: "there"}",
                "Your library at a glance",
            )
        },
    )
}

@Composable
private fun GamesScreen(client: ApiClient, padding: PaddingValues) {
    NativeDataContent(
        client = client,
        path = "/api/game/list",
        modifier = Modifier.padding(padding),
        header = { ScreenHeader("Games", "Your complete game library") },
        preferredTitleKeys = listOf("title", "name"),
    )
}

private data class NativeDestination(val title: String, val path: String, val subtitle: String)

private val destinations = listOf(
    NativeDestination("Collections", "/api/sets", "Curated groups and sets"),
    NativeDestination("Inbox", "/api/media/inbox", "Unassigned captures"),
    NativeDestination("Bounties", "/api/bounties", "Challenges and objectives"),
    NativeDestination("Cards", "/api/cards", "Completion cards"),
    NativeDestination("Statistics", "/api/stats/overview", "Progress and activity"),
    NativeDestination("Provider connections", "/api/settings/provider-credentials", "Connected game services"),
    NativeDestination("API keys", "/api/auth/api-keys", "Personal access credentials"),
)

@Composable
private fun MoreScreen(
    padding: PaddingValues,
    onOpen: (NativeDestination) -> Unit,
    onLogout: () -> Unit,
    onChangeServer: () -> Unit,
) {
    LazyColumn(
        Modifier.fillMaxSize().padding(padding),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { ScreenHeader("More", "Settings, activity, and tools") }
        items(destinations) { destination ->
            Card(onClick = { onOpen(destination) }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                Column(Modifier.padding(18.dp)) {
                    Text(destination.title, fontWeight = FontWeight.SemiBold)
                    Text(destination.subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        item {
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = onChangeServer, modifier = Modifier.fillMaxWidth()) { Text("Change server") }
            TextButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) { Text("Sign out") }
        }
    }
}

@Composable
private fun NativeDataScreen(client: ApiClient, destination: NativeDestination, padding: PaddingValues, onBack: () -> Unit) {
    NativeDataContent(
        client,
        destination.path,
        Modifier.padding(padding),
        header = {
            Column {
                TextButton(onClick = onBack) { Text("Back") }
                ScreenHeader(destination.title, destination.subtitle)
            }
        },
    )
}

@Composable
private fun NativeDataContent(
    client: ApiClient,
    path: String,
    modifier: Modifier = Modifier,
    header: @Composable () -> Unit,
    preferredTitleKeys: List<String> = listOf("title", "name", "username", "provider"),
) {
    var data by remember(path, client) { mutableStateOf<JsonElement?>(null) }
    var error by remember(path, client) { mutableStateOf<String?>(null) }
    var refresh by remember { mutableIntStateOf(0) }
    LaunchedEffect(path, client, refresh) {
        data = null
        error = null
        try { data = client.get(path) } catch (exception: Exception) { error = exception.message }
    }
    LazyColumn(
        modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { header() }
        when {
            error != null -> item {
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                    Column(Modifier.padding(18.dp)) {
                        Text(error!!)
                        TextButton(onClick = { refresh++ }) { Text("Try again") }
                    }
                }
            }
            data == null -> item { Box(Modifier.fillMaxWidth().padding(40.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() } }
            data is JsonArray -> {
                val values = (data as JsonArray).toList()
                if (values.isEmpty()) item { EmptyCard() }
                items(values) { value -> JsonCard(value, preferredTitleKeys) }
            }
            data is JsonObject -> {
                val entries = (data as JsonObject).entries.toList()
                if (entries.isEmpty()) item { EmptyCard() }
                items(entries) { (key, value) -> JsonCard(JsonObject(mapOf("label" to JsonPrimitive(key), "value" to value)), listOf("label")) }
            }
            else -> item { JsonCard(data!!, preferredTitleKeys) }
        }
    }
}

@Composable
private fun EmptyCard() {
    Card(Modifier.fillMaxWidth()) { Text("Nothing here yet.", Modifier.padding(20.dp), color = MaterialTheme.colorScheme.onSurfaceVariant) }
}

@Composable
private fun JsonCard(value: JsonElement, titleKeys: List<String>) {
    val obj = value as? JsonObject
    val title = titleKeys.firstNotNullOfOrNull { obj.string(it) }
        ?: (value as? JsonPrimitive)?.contentOrNull
        ?: "Details"
    val details = obj?.entries
        ?.filter { it.key !in titleKeys && it.value !is JsonNull }
        ?.take(6)
        .orEmpty()
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title.humanize(), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            details.forEach { (key, detail) ->
                Text(
                    "${key.humanize()}: ${detail.displayValue()}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

private fun JsonObject?.string(key: String): String? =
    ((this?.get(key) as? JsonPrimitive)?.contentOrNull)?.takeIf { it.isNotBlank() }

private fun JsonElement.displayValue(): String = when (this) {
    is JsonPrimitive -> contentOrNull ?: toString()
    is JsonArray -> if (isEmpty()) "None" else "${size} items"
    is JsonObject -> if (isEmpty()) "None" else entries.take(3).joinToString { "${it.key.humanize()} ${it.value.displayValue()}" }
    else -> "None"
}

private fun String.humanize(): String = replace('_', ' ').replaceFirstChar { it.uppercase() }
