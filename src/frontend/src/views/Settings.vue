<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { currentUser } from '../state/auth'
import SettingsNav from '../components/settings/SettingsNav.vue'
import type { SettingsGroup } from '../components/settings/SettingsNav.vue'
import ProfileSection from '../components/settings/ProfileSection.vue'
import InterfaceSection from '../components/settings/InterfaceSection.vue'
import UploadSection from '../components/settings/UploadSection.vue'
import LibraryManagementSection from '../components/settings/LibraryManagementSection.vue'
import ScanSettingsSection from '../components/settings/ScanSettingsSection.vue'
import MetadataSourcesSection from '../components/settings/MetadataSourcesSection.vue'
import AdminSection from '../components/settings/AdminSection.vue'
import StatsSection from '../components/settings/StatsSection.vue'
import ComingSoonSection from '../components/settings/ComingSoonSection.vue'

const router = useRouter()

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

const groups = computed<SettingsGroup[]>(() => {
  const result: SettingsGroup[] = [
    {
      label: 'Account',
      sections: [
        { id: 'profile', label: 'Profile' },
        { id: 'interface', label: 'User Interface' },
      ],
    },
    {
      label: 'Library',
      sections: [
        { id: 'upload', label: 'Upload' },
        { id: 'library', label: 'Library Management' },
      ],
    },
    {
      label: 'Metadata',
      sections: [
        { id: 'scan', label: 'Scan Settings' },
        { id: 'sources', label: 'Metadata/API' },
        { id: 'export', label: 'Export / Import', comingSoon: true },
      ],
    },
  ]

  const systemSections = [
    ...(currentUser.value?.is_admin ? [{ id: 'admin', label: 'Admin' }] : []),
    { id: 'stats', label: 'Server Stats' },
    ...(currentUser.value?.is_admin ? [{ id: 'tasks', label: 'Tasks', comingSoon: true }] : []),
    ...(currentUser.value?.is_admin ? [{ id: 'logs', label: 'Logs', comingSoon: true }] : []),
  ]
  result.push({ label: 'System', sections: systemSections })

  return result
})

const activeSection = ref('profile')
</script>

<template>
  <main class="settings-page">
    <button type="button" class="back-arrow-button" title="Back" @click="goBack">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 12H5" />
        <path d="M12 19l-7-7 7-7" />
      </svg>
    </button>

    <div class="settings-layout">
      <h1>Settings</h1>
      <div class="settings-body">
        <SettingsNav v-model:active-section="activeSection" :groups="groups" />

        <div class="settings-card">
          <ProfileSection v-if="activeSection === 'profile'" />
          <InterfaceSection v-else-if="activeSection === 'interface'" />
          <UploadSection v-else-if="activeSection === 'upload'" />
          <LibraryManagementSection v-else-if="activeSection === 'library'" />
          <ScanSettingsSection v-else-if="activeSection === 'scan'" />
          <MetadataSourcesSection v-else-if="activeSection === 'sources'" />
          <AdminSection v-else-if="activeSection === 'admin' && currentUser?.is_admin" />
          <StatsSection v-else-if="activeSection === 'stats'" />
          <ComingSoonSection
            v-else-if="activeSection === 'export'"
            title="Export / Import"
            description="Export your library to a portable file and import it back — for backups or moving to a new server."
            :planned-features="[
              'Full library export to a single portable file',
              'Import from a previous export',
              'Selective export (by collection, status, or tag)',
            ]"
          />
          <ComingSoonSection
            v-else-if="activeSection === 'tasks' && currentUser?.is_admin"
            title="Tasks"
            description="Schedule recurring jobs, run by an in-process scheduler — no extra server required."
            :planned-features="[
              'Scheduled metadata refreshes',
              'Automatic library rescans',
              'Storage cleanup jobs',
            ]"
          />
          <ComingSoonSection
            v-else-if="activeSection === 'logs' && currentUser?.is_admin"
            title="Logs"
            description="An audit trail of edits made across the library, including changes made by other users."
            :planned-features="[
              'Who changed what, and when',
              'Filter by user, game, or field',
              'Restore a previous value',
            ]"
          />
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.settings-page {
  position: relative;
  min-height: 100vh;
  padding: 84px 40px 40px;
  background: #121212;
  font-family: system-ui, sans-serif;
}
.back-arrow-button {
  position: fixed;
  top: 16px;
  left: 62px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: background 0.15s ease;
}
.back-arrow-button:hover {
  background: rgba(40, 40, 40, 0.85);
}
.settings-layout {
  width: 100%;
  color: #fff;
}
.settings-layout h1 {
  margin: 0 0 24px;
  font-size: 1.5rem;
}
.settings-body {
  display: flex;
  gap: 32px;
  align-items: flex-start;
}
.settings-card {
  flex: 1;
  min-width: 0;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 14px;
  padding: 32px;
}
</style>
