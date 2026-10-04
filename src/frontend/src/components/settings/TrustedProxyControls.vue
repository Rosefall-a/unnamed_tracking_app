<script setup lang="ts">
import { onMounted, ref } from "vue";
interface Preset { label: string; values: string[]; }
const props=defineProps<{modelValue:string;disabled?:boolean}>();
const emit=defineEmits<{"update:modelValue":[value:string]}>();
const presets=ref<Record<string,Preset>>({}); const custom=ref(""); const error=ref<string|null>(null);
const tokens=(v:string)=>v.split(/\s+/).map(x=>x.trim()).filter(Boolean);
function add(values:string[]){const merged=[...tokens(props.modelValue)];for(const v of values)if(!merged.includes(v))merged.push(v);emit("update:modelValue",merged.join(" "))}
function addCustom(){error.value=null;const values=tokens(custom.value);if(!values.length)return;if(values.some(v=>!/^[0-9A-Fa-f:.\/]+$/.test(v))){error.value="Custom entries must be IP addresses or CIDR ranges.";return}add(values);custom.value=""}
onMounted(async()=>{try{const r=await fetch("/api/internal/real-ip/presets",{credentials:"include"});if(!r.ok)throw new Error();presets.value=(await r.json()).presets}catch{error.value="Unable to load proxy presets."}});
</script>
<template><div class="proxy-controls"><div class="preset-buttons"><button v-for="(p,k) in presets" :key="k" type="button" :disabled="disabled" @click="add(p.values)">Enable {{p.label}}</button></div><input :value="modelValue" :disabled="disabled" placeholder="127.0.0.1/32 ::1/128" @input="emit('update:modelValue',($event.target as HTMLInputElement).value)"/><div class="custom-row"><input v-model="custom" :disabled="disabled" placeholder="Custom IP/CIDR ranges"/><button type="button" :disabled="disabled||!custom.trim()" @click="addCustom">Add custom</button></div><small>Loopback is the safe default. Presets add trusted proxy ranges; environment-managed values are locked.</small><small v-if="error" class="error">{{error}}</small></div></template>
<style scoped>.proxy-controls{display:flex;flex-direction:column;gap:8px}.preset-buttons{display:flex;flex-wrap:wrap;gap:8px}.proxy-controls input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.custom-row{display:flex;gap:8px}.custom-row input{flex:1}.proxy-controls button{background:#252525;color:#ddd;border:1px solid #3a3a3a;border-radius:8px;padding:8px 10px;cursor:pointer}.proxy-controls small{color:#777;font-size:11px}.proxy-controls .error{color:#fca5a5}</style>
