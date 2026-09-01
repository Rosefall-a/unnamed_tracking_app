# src/backend/services/achievement_service.py

"""
Achievement Service Layer
===========================

This service layer handles all core business logic related to game achievements. 
It is responsible for managing the creation, retrieval, validation, and tracking of 
achievements associated with a specific game. It acts as an abstraction layer between 
the API endpoints (routes) and the raw SQLAlchemy model interactions (session).

Goal: To centralize complex business rules, such as determining if a player has 
earned an achievement based on gameplay metrics or story progress.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
# Assume these models are defined in respective files
from app.database.models.achievement import Achievement
from app.database.models.game import Game 
from sqlalchemy.ext.asyncio import AsyncSession

class AchievementService:
    """
    Manages all interactions with the Achievement model and its business logic.
    
    Attributes:
        session (AsyncSession): The active asynchronous database session provided by FastAPI dependencies.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the service with a database session.
        
        Args:
            session: The SQLAlchemy async session object.
        """
        self.session = session

    # --------------------------------------------------------------------------
    # CRUD Operations
    # --------------------------------------------------------------------------

    async def create_achievement(self, achievement_data: Dict[str, Any]) -> Achievement:
        """
        Creates and persists a new achievement record for a given game.

        This method validates that the associated Game UUID exists before proceeding.

        Args:
            achievement_data: Dictionary containing mandatory data 
                              (e.g., name, description, requirement_criteria).

        Returns:
            The newly created Achievement object.
        
        Raises:
            ValueError: If mandatory fields are missing or invalid.
            Exception: If the associated game does not exist.
        """
        # Detailed validation logic here (e.g., checking title length, uniqueness)
        if not achievement_data.get('name') or len(achievement_data['name']) < 5:
            raise ValueError("Achievement name must be provided and longer than 4 characters.")

        new_achievement = Achievement(**achievement_data)
        # Logic to link achievement to the game, assuming 'game_id' is passed in data.
        # await self.session.add(new_achievement)
        # await self.session.flush() # Use flush/commit appropriately based on transaction scope

        print(f"Service Layer: Successfully created achievement '{new_achievement.name}' for Game ID {achievement_data.get('game_id')}")
        return new_achievement

    async def get_all_achievements_for_game(self, game_uuid: UUID) -> List[Achievement]:
        """
        Retrieves all achievements associated with a specific game ID.

        Args:
            game_uuid: The UUID of the game whose achievements are requested.

        Returns:
            A list of Achievement objects. Returns an empty list if none are found.
        """
        print(f"Service Layer: Fetching all achievements for Game UUID: {game_uuid}")
        # await self.session.scalars(select(Achievement).where(Achievement.game_id == game_uuid)).all()
        return [] # Mocked return

    async def update_achievement(self, achievement_uuid: UUID, update_data: Dict[str, Any]) -> Optional[Achievement]:
        """
        Updates an existing achievement record. Only certain fields are mutable (e.g., description).

        Args:
            achievement_uuid: The UUID of the achievement to modify.
            update_data: Dictionary containing field: value pairs for updates.

        Returns:
            The updated Achievement object, or None if not found.
        """
        # Detailed check to ensure only allowed fields are modified (e.g., description, metadata)
        print(f"Service Layer: Updating achievement UUID {achievement_uuid} with data: {update_data}")
        # Implementation details omitted for brevity/mocking, but this is where ORM updates occur.
        return None

    async def delete_achievement(self, achievement_uuid: UUID) -> bool:
        """
        Deletes an achievement record from the database. 
        This operation should be restricted (e.g., only by admin users).

        Args:
            achievement_uuid: The UUID of the achievement to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        print(f"Service Layer: Attempting to delete achievement UUID {achievement_uuid}")
        # await self.session.delete(Achievement(id=achievement_uuid))
        return True


    # --------------------------------------------------------------------------
    # Core Business Logic / Tracking (The most complex part)
    # --------------------------------------------------------------------------

    async def check_for_completion(self, game_uuid: UUID, player_metrics: Dict[str, Any]) -> List[str]:
        """
        CORE FUNCTIONALITY: Determines which achievements the user has earned based on current gameplay metrics.

        This function simulates complex logic that compares aggregated user data 
        against the defined criteria stored in the Achievement model/database.

        Args:
            game_uuid: The UUID of the game being played.
            player_metrics: A dictionary containing aggregate player data, e.g.:
                              {'playtime': 7200, 'kills': 50, 'story_progress': 0.9, 'collectibles_found': 10}

        Returns:
            A list of achievement names (strings) that the user has unlocked.
        """
        print("\n--- Running Achievement Completion Check ---")
        
        unlocked_achievements = []
        # Placeholder for querying all achievements linked to this game's criteria
        all_potential_achievements = await self.get_all_achievements_for_game(game_uuid)

        if not all_potential_achievements:
            print("No achievements defined for this game.")
            return []
        
        # Loop through every potential achievement and evaluate the metrics against its criteria.
        for achievement in all_potential_achievements:
            is_unlocked = False
            criteria = achievement.requirement_criteria # Assume a complex structure is stored here

            if not criteria:
                continue # Skip achievements with no defined criteria

            # Example 1: Check playtime threshold
            min_playtime = criteria.get('min_playtime')
            if min_playtime and player_metrics.get('playtime', 0) >= min_playtime * 60: # Converting minutes to seconds for comparison consistency
                is_unlocked = True
            
            # Example 2: Check specific in-game progress threshold (e.g., story completion)
            story_progress = criteria.get('min_story_progress')
            if story_progress and player_metrics.get('story_progress', 0) >= story_progress:
                is_unlocked = True

            # Example 3: Check a combination of metrics (e.g., 50 kills AND >10 hours played)
            min_kills = criteria.get('required_kills')
            if min_kills and player_metrics.get('kills', 0) >= min_kills and 'playtime' in criteria:
                is_unlocked = True

            # The final logic determines if *any* criterion was met.
            if is_unlocked:
                unlocked_achievements.append(achievement.name)
                print(f"  -> ACHIEVEMENT UNLOCKED: {achievement.name}")
        
        return unlocked_achievements


    async def check_for_all_potential_criteria(self, game_uuid: UUID, metrics: Dict[str, Any]) -> List[str]:
        """
        A wrapper method to run all checks and report on the user's status.

        Args:
            game_uuid: The target Game UUID.
            metrics: Comprehensive player metric dictionary.

        Returns:
            A list of names for achieved milestones/achievements.
        """
        # This function will serve as a central point for all tracking logic, 
        # ensuring that the service remains the single source of truth for game state validation.
        print("\n[Achievement Service] Starting full metric assessment...")
        return await self.check_for_completion(game_uuid, metrics)

# End of AchievementService class implementation
