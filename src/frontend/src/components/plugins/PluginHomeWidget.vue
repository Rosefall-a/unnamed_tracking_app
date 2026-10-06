<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import PluginContributionHost from "./PluginContributionHost.vue";
import type { PluginSlotContribution } from "../../state/pluginExtensions";
import type { UiValues } from "../../services/pluginUi";
import { widgetConfiguration } from "../../services/homeWidgets";

const props = defineProps<{
  contribution: PluginSlotContribution;
  saved: UiValues;
}>();
const phone = window.matchMedia("(max-width: 760px)");
const mobile = ref(phone.matches);
const changed = () => {
  mobile.value = phone.matches;
};
phone.addEventListener("change", changed);
onBeforeUnmount(() => phone.removeEventListener("change", changed));
const pageId = computed(() =>
  mobile.value && props.contribution.widget?.mobile_page_id
    ? props.contribution.widget.mobile_page_id
    : props.contribution.page.id,
);
const configuration = computed(() =>
  widgetConfiguration(
    props.contribution.widget?.configuration ?? [],
    props.saved,
  ),
);
const context = computed(() => ({
  host_page: "home",
  widget_id: props.contribution.extensionId,
  mobile: mobile.value,
  widget_configuration: JSON.stringify(configuration.value),
}));
</script>

<template>
  <PluginContributionHost
    :plugin-id="contribution.pluginId"
    :page-id="pageId"
    :key="pageId"
    :document="contribution.document"
    :context="context"
    :widget-config="configuration"
    embedded
  />
</template>
