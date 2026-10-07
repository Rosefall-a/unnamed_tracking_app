<script setup lang="ts">
// Off by default: a Steam import only brings in the games you own. With this on
// it also adds your Steam wishlist, as Wishlist games.
import { ref, onMounted } from "vue";
import ToggleButton from "./ToggleButton.vue";
import { fetchPreferences, queuePreferences } from "../../services/preferences";
import { preferences as sharedPreferences } from "../../state/preferences";

const enabled = ref(false);
const error = ref<string | null>(null);
const savedNote = ref("");

onMounted(async () => {
  try {
    enabled.value = (await fetchPreferences()).steam_import_wishlist;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load settings.";
  }
});

async function change(next: boolean) {
  const previous = enabled.value;
  enabled.value = next;
  error.value = null;
  try {
    const { prefs, latest } = await queuePreferences({
      steam_import_wishlist: next,
    });
    if (latest) {
      enabled.value = prefs.steam_import_wishlist;
      sharedPreferences.value = prefs;
    }
    savedNote.value = "Saved";
    setTimeout(() => (savedNote.value = ""), 1500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save.";
    enabled.value = previous;
  }
}
</script>

<template>
  <section class="settings-section steam-wishlist">
    <h2>Steam wishlist</h2>
    <p class="section-hint">
      With this on, importing from Steam also adds the games on your Steam
      wishlist, marked as Wishlist. Your Steam game details must be public for
      Steam to share the wishlist. A game you later buy becomes a normal game on
      the next import. Turning this off never removes games already added.
      <span v-if="savedNote" class="saved">{{ savedNote }}</span>
    </p>
    <ToggleButton
      :model-value="enabled"
      label="Import my Steam wishlist"
      @update:model-value="change"
    >
      <strong>Import my Steam wishlist</strong>
    </ToggleButton>
    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<style scoped>
.steam-wishlist {
  margin-top: 36px;
}
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  font-size: 1rem;
  color: #fff;
}
.section-hint {
  color: #999;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.saved {
  margin-left: 8px;
  color: #d68a34;
  font-weight: 700;
}
.error {
  color: #fca5a5;
  font-size: 0.85rem;
}
</style>
