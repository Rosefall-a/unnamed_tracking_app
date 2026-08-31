/**
 * @file src/tests/frontend/games.test.ts
 * @description Unit tests for the game data service layer, ensuring proper mapping and API interaction mocking.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as gamesService from '../../src/services/games';
import type { Game, BackendGame } from '../../src/types/game'

// Mock the entire fetch API globally for these tests
vi.mock('fetch', async (args: RequestInfo | URL, init?: RequestInit) => {
  if (typeof args === 'string') {
    const url = new URL(args);
    switch (url.pathname) {
      case '/api/game/list':
        // Mock successful list response
        return {
          ok: true,
          statusText: '',
          json: async () => [
            { // Game 1 Data
              id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
              title: 'Elden Ring',
              sort_title: 'Elden Ring',
              description: 'A vast open world RPG.',
              release_date: '2022-02-25',
              developer: 'FromSoftware',
              publisher: 'Bandai Namco Entertainment',
              status: 'PLAYED', // Test different status values
              priority: 'High',
              favorite: true,
              notes: 'Loved this game!',
              resume_note: null,
              playtime_seconds: 60 * 150 + 30 * 2, // 150 minutes 2 hours = 9300 seconds
              rating_story: 4.8,
              rating_gameplay: 4.9,
              rating_soundtrack: 5.0,
              rating_overall: 4.9,
              personal_rank: 1,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            },
            { // Game 2 Data - Minimal/Partial Data
              id: 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
              title: 'Indie Gem',
              sort_title: 'Indie Gem',
              description: null,
              release_date: '2024-10-01',
              developer: 'Indie Dev Co.',
              publisher: null,
              status: 'WISHLIST',
              priority: null,
              favorite: false,
              notes: null,
              resume_note: null,
              playtime_seconds: 0, // New game / never played
              rating_story: null,
              rating_gameplay: null,
              rating_soundtrack: null,
              rating_overall: null,
              personal_rank: null,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            }
          ] as BackendGame[],
        );
      case '/api/game/get/:id':
        // Mock single game retrieval (for ID 1)
        if (args.includes('/a0eebc99')) {
          return {
            ok: true,
            statusText: '',
            json: async () => ({
              id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
              title: 'Elden Ring',
              sort_title: 'Elden Ring',
              description: 'A vast open world RPG.',
              release_date: '2022-02-25',
              developer: 'FromSoftware',
              publisher: 'Bandai Namco Entertainment',
              status: 'PLAYED',
              priority: 'High',
              favorite: true,
              notes: 'Loved this game!',
              resume_note: null,
              playtime_seconds: 9300,
              rating_story: 4.8,
              rating_gameplay: 4.9,
              rating_soundtrack: 5.0,
              rating_overall: 4.9,
              personal_rank: 1,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            } as BackendGame)
          }
        } else {
          // Mock Not Found for other IDs
          return { ok: false, statusText: 'Not Found' }
        }
      case '/api/game/:id/notes':
        const gameIdMatch = args.match(/\/api\/game\/([a-f0-9-]+)\/notes/);
        const id = gameIdMatch ? gameIdMatch[1] : '';

        // Mock list notes endpoint
        if (args.includes('/notes')) {
          return {
            ok: true,
            statusText: '',
            json: async () => ({
              notes: ['A fantastic journey.', 'Great atmosphere and challenging combat.'],
            }),
          }
        }
        // Mock fetch note content
        if (args.includes('/notes/title')) {
             return { ok: true, statusText: '', text: async () => 'The initial story notes are here.' }
        }

        // Mock save/update note endpoint (PUT)
        if (args.includes('/notes/')) {
            return {
                ok: true, 
                statusText: '', 
                json: async () => ({ game_id: id, note_name: 'title', status: 'saved' })
            }
        }

        // Mock delete note endpoint (DELETE)
        if (args.includes('/notes/')) {
             return { ok: true, statusText: '', json: async () => ({ game_id: id, note_name: 'title', status: 'deleted' }) }
        }

        return { ok: false, statusText: 'Bad Request Mock' };
  }
});


describe('Games Service Layer', () => {
  // --- Data Mapping Tests (Core Logic) ---
  it('should correctly map raw backend data to the frontend Game type', async () => {
    const mockRawData: BackendGame = {
      id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
      title: 'Elden Ring',
      sort_title: 'Elden Ring',
      description: 'A vast open world RPG.',
      release_date: '2022-02-25',
      developer: 'FromSoftware',
      publisher: 'Bandai Namco Entertainment',
      status: 'PLAYED', 
      priority: 'High',
      favorite: true,
      notes: 'Loved this game!',
      resume_note: null,
      playtime_seconds: 9300, // 155 minutes
      rating_story: 4.8,
      rating_gameplay: 4.9,
      rating_soundtrack: 5.0,
      rating_overall: 4.9,
      personal_rank: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    } as unknown as BackendGame

    const mappedGame = gamesService.mapBackendGame(mockRawData)
    
    expect(mappedGame.title).toBe('Elden Ring')
    expect(mappedGame.status).toEqual('PLAYED' as any) // Check enum mapping
    expect(mappedGame.ratingOverall).toBe(4.9)
    expect(typeof mappedGame.platforms[0].playtimeMinutes).toBe('number')
    expect(mappedGame.developer).toBe('FromSoftware')
  })

  // --- Core Fetching Tests (Integration Logic) ---
  describe('fetchGames', () => {
    it('should fetch and map an array of games successfully', async () => {
      const games = await gamesService.fetchGames()
      expect(games).toHaveLength(2)
      expect(games[0].title).toBe('Elden Ring')
      expect(games[1].status).toBe('WISHLIST'); // Check the second mocked game status
    })

    it('should throw an error if fetching games fails due to bad response', async () => {
      // Override mock to simulate failure for this test case
      vi.mocked(fetch).mockResolvedValue({
        ok: false,
        statusText: 'Server Error',
        json: async () => ({ message: 'Internal Server Error' }),
      })

      await expect(gamesService.fetchGames()).rejects.toThrow('Failed to fetch games: 404 Not Found');
    })
  })

  describe('fetchGame', () => {
    it('should successfully retrieve and map a single game by ID', async () => {
        const game = await gamesService.fetchGame('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
        expect(game).not.toBeNull()
        expect(game)!.title).toBe('Elden Ring');
    });

    it('should return null if the game ID is not found (404)', async () => {
        // Mocking fetch for a non-existent ID to hit the 404 case mocked earlier
        vi.mocked(fetch).mockResolvedValue({
            status: 404,
            ok: false,
            statusText: 'Not Found',
        });

        const game = await gamesService.fetchGame('non-existent-uuid');
        expect(game).toBeNull();
    });
  })


  // --- Notes Feature Tests (CRUD) ---
  describe('Game Note Management', () => {
    const mockGameId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'

    it('should list existing game notes correctly', async () => {
      const notes = await gamesService.listGameNotes(mockGameId);
      expect(notes).toEqual(['A fantastic journey.', 'Great atmosphere and challenging combat.']);
    });

    it('should fetch the content of a specific note', async () => {
        const content = await gamesService.fetchGameNote(mockGameId, 'title');
        expect(content).toBe('The initial story notes are here.');
    });

    it('should successfully save/update a game note', async () => {
      const response = await gamesService.saveGameNote(
        mockGameId, 
        'title', 
        'Updated content to test persistence.'
      );
      expect(response.status).toBe('saved');
    });

    it('should successfully delete a game note', async () => {
      const response = await gamesService.deleteGameNote(mockGameId, 'title');
      expect(response.status).toBe('deleted');
    });
  })

  // --- Asset Upload Test (File Handling) ---
  describe('Asset Management', () => {
    it('should successfully upload a game asset using FormData', async () => {
        // Mocking file object creation for testing purposes
        const mockFile = new File(['mock content'], 'test_art.png', { type: 'image/png' });

        // We don't need to check the return value structure, just that the API call is structured correctly
        await expect(gamesService.uploadGameAsset(
            'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 
            'key_art', 
            mockFile
          )).resolves.toEqual({
              game_id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
              asset_kind: 'key_art',
              path: expect.any(String), // Path will be dynamically generated
              status: 'success'
          });
    })
  })
})