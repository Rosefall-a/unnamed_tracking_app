// Saving an edit to a collection. A collection is only a tag on its games, so
// renaming one means moving that tag on every member; a smart collection is a
// rule, so it renames in place. Everything stored locally under the old name
// (cover pick, order, description, pin) follows.
import {
  addGameToCollection,
  removeGameFromCollection,
} from "../services/games";
import type { Game } from "../types/game";
import {
  removeSmartCollection,
  updateSmartCollection,
} from "../state/smartCollections";
import {
  forgetCollectionKeys,
  renameCollectionKeys,
  updateMeta,
} from "../state/collectionMeta";
import type { CollectionFormPayload } from "../components/CollectionFormModal.vue";

export async function saveCollectionEdit(args: {
  oldName: string;
  payload: CollectionFormPayload;
  // set for a smart collection: its rule's id
  smartId?: string;
  // the games currently in it, only needed to rename a manual one
  members: Game[];
}): Promise<void> {
  const { oldName, payload, smartId, members } = args;
  const name = payload.name;

  if (smartId && payload.smart) {
    updateSmartCollection(smartId, {
      name,
      field: payload.smart.field,
      value: payload.smart.value,
    });
  } else if (name !== oldName) {
    for (const game of members) {
      await addGameToCollection(game.id, name);
      await removeGameFromCollection(game.id, oldName);
    }
  }
  renameCollectionKeys(oldName, name);
  updateMeta(name, { description: payload.description ?? undefined });
}

// Deleting a manual collection takes the tag off every game in it (no game is
// deleted); deleting a smart one only removes its rule.
export async function deleteCollectionFully(args: {
  name: string;
  members: Game[];
  smartId?: string;
}): Promise<void> {
  if (args.smartId) {
    removeSmartCollection(args.smartId);
  } else {
    for (const game of args.members) {
      await removeGameFromCollection(game.id, args.name);
    }
  }
  forgetCollectionKeys(args.name);
}
