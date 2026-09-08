// shared open/closed flag, lets other pages' own Escape/keydown handlers
// (e.g. GameLibrary's "Escape clears search") know to back off while the
// palette is up, since it's a fixed overlay mounted once in App.vue rather
// than scoped to whichever page opened it
import { ref } from 'vue'

export const isCommandPaletteOpen = ref(false)
