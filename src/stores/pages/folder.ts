import { ComputedRef } from "vue";
import { defineStore } from "pinia";

import { useFuse } from "@/utils";

import fetchThem from "@/composables/fetch/folders";
import { FuseTrackOptions } from "@/composables/enums";
import { Folder, Track, FussResult } from "@/interfaces";

export default defineStore("FolderDirs&Tracks", {
  state: () => ({
    query: "",
    path: <string>{},
    allDirs: <Folder[]>[],
    allTracks: <Track[]>[],
  }),
  actions: {
    async fetchAll(path: string) {
      const { tracks, folders } = await fetchThem(path);

      [this.path, this.allDirs, this.allTracks] = [path, folders, tracks];
    },
  },
  getters: {
    filteredTracks(): ComputedRef<FussResult[]> {
      return useFuse(this.query, this.allTracks, FuseTrackOptions);
    },
    tracks(): Track[] {
      const tracks = this.filteredTracks.value.map((result: FussResult) => {
        const t = {
          ...result.item,
          index: result.refIndex,
        };

        return t;
      });

      return tracks;
    },
    dirs(): Folder[] {
      const dirs = useFuse(this.query, this.allDirs, {
        keys: ["name"],
      });

      return dirs.value.map((result) => {
        return result.item;
      });
    },
  },
});
