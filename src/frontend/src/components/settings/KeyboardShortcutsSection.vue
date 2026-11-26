<script setup lang="ts">
import { SHORTCUT_GROUPS } from "../../utils/shortcuts";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
</script>

<template>
  <p class="st-muted intro">
    Press <span class="st-kbd">?</span> anywhere to open this list. Each
    shortcut works on the page it is listed under.
  </p>
  <SettingsCard
    v-for="group in SHORTCUT_GROUPS"
    :key="group.title"
    :title="group.title"
  >
    <SettingsRow v-for="s in group.shortcuts" :key="s.label" :label="s.label">
      <span class="st-kbd">{{ s.keys }}</span>
    </SettingsRow>
  </SettingsCard>
</template>

<style scoped>
.intro {
  margin: 0;
}
</style>
