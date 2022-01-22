import { ref } from "@vue/reactivity";

const search_query = ref("");

const queue = ref([
  {
    title: "Nothing played yet",
    artists: ["... blah blah blah"],
    image: "http://0.0.0.0:8900/images/defaults/5.webp",
    _id: {
      $oid: "",
    },
  },
]);

const folder_song_list = ref([]);
const folder_list = ref([]);

const current = ref({
  title: "Nothing played yet",
  artists: ["... blah blah blah"],
  image: "http://0.0.0.0:8900/images/defaults/1.webp",
  _id: {
    $oid: "",
  },
});

const prev = ref({
  title: "The previous song",
  artists: ["... blah blah blah"],
  _id: {
    $oid: "",
  },
});

const album_song_list = ref([]);
const album_info = ref([]);
const album_artists = ref([]);
const album_bio = ref("");

const filters = ref([]);

const magic_flag = ref(false);
const loading = ref(false);

const is_playing = ref(false);

const search_tracks = ref([]);
const search_albums = ref([]);
const search_artists = ref([]);

export default {
  search_query,
  queue,
  folder_song_list,
  folder_list,
  current,
  prev,
  filters,
  magic_flag,
  loading,
  is_playing,
  search_tracks,
  search_albums,
  search_artists,
  album_song_list,
  album_info,
  album_artists,
  album_bio,
};