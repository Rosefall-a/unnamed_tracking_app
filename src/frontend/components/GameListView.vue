<template>
  <div>
    <h1>Game Tracker Dashboard</h1>
    <div class="game-list">
      <div v-if="loading" class="card loading">Loading games...</div>
      <div v-else-empty>No games found in the database. Add a new game!</div>

      <div v-for="game in games" :key="game.id" class="game-card">
        <h3>{{ game.title }}</h3>
        <p class="description">{{ game.description || 'No description provided.' }}</p>
        <div class="metadata">
          <span>Status: <strong>{{ formatStatus(game.status) }}</strong></span>
          <span>Playtime: {{ (game.playtime_seconds / 60).toFixed(1) }} hours</span>
          <!-- Add more metadata like Developer name -->
        </div>
        <button @click="viewGameDetails(game.id)">View Details</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
// Import the new API service layer for centralized communication
import { ApiService } from '@/backend/api_service'; 

const games = ref([]);
const loading = ref(true);

const fetchGames = async () => {
  loading.value = true;
  try {
    // Initialize and use the dedicated API Service instance
    const apiService = new ApiService();
    const gameList = await apiService.get_all_games(); 
    
    if (gameList) {
        // Assuming get_all_games returns a list of games objects directly
        games.value = gameList;
    } else {
        console.warn("Received no game data from the API service.");
        // Handle case where endpoint exists but is empty or unparseable structure
        games.value = [];
    }

  } catch (error) {
    console.error("Failed to fetch games:", error);
    alert("Could not connect to API or an API error occurred. Ensure the backend service is running.");
  } finally {
    loading.value = false;
  }
};

const viewGameDetails = (gameId) => {
    console.log(`Navigating to details for Game ID: ${gameId}`);
    // Future logic: Router navigation or opening a modal
};

const formatStatus = (status) => {
    switch(status) {
        case 'PLAYED': return '✅ Played';
        case 'WISHLIST': return '⭐ Wishlist';
        case 'BACKLOG': return '📥 Backlog';
        default: return status;
    }
};

onMounted(() => {
  fetchGames();
});
</script>

<style scoped>
.game-card {
  border: 1px solid #ccc;
  padding: 20px;
  margin-bottom: 15px;
  border-radius: 8px;
}
.metadata span {
    margin-right: 20px;
}
</style>