import pytest
from datetime import date, datetime
from uuid import UUID, uuid4
# Mocking the necessary SQLAlchemy components for isolated testing
from sqlalchemy import create_engine, Column, String, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Setup Mock Base and Models (Ideally done in conftest.py) ---
Base = declarative_base()

class GameStatus:
    """Mock Enum equivalent"""
    DROPPED = "DROPPED"
    WISHLIST = "WISHLIST"
    BACKLOG = "BACKLOG"
    ON_HOLD = "ON_HOLD"
    PLAYING = "PLAYING"
    PLAYED = "PLAYED"
    BEATEN = "BEATEN"
    MASTERED = "MASTERED"

# Mock Game and Developer models to allow testing dependencies
class Developer(Base):
    id: UUID = mapped_column(primary_key=True)
    name: str = mapped_column(String, unique=True)
    games: list["Game"] = relationship("Game", back_populates="developer")

class Game(Base):
    __tablename__ = "games"
    id: UUID = mapped_column(primary_key=True)
    folder_location: str = mapped_column(String, unique=True, nullable=False)
    title: str = mapped_column(String, nullable=False)
    description: str | None = mapped_column(Text, nullable=True)
    status: GameStatus = mapped_column(String, default=GameStatus.WISHLIST, nullable=False)
    developer_id: UUID = mapped_column(ForeignKey("developers.id"))
    developer: "Developer" = relationship("Developer", back_populates="games")
    achievements: list["Achievement"] = relationship("Achievement", back_populates="game")

class Achievement(Base):
    __tablename__ = "achievements"
    id: UUID = mapped_column(primary_key=True)
    game_id: UUID = mapped_column(ForeignKey("games.id"), nullable=False)
    name: str = mapped_column(String, nullable=False)
    description: str | None = mapped_column(Text, nullable=True)

# --- Fixtures and Tests ---

@pytest.fixture
def db_session():
    """Mock SQLAlchemy Session fixture for in-memory testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        yield db

def test_achievement_creation_and_linking(db_session):
    """Tests linking and creation of achievements to a specific game."""
    # Setup Game (Must exist for achievement FK)
    game_uuid = uuid4()
    game = Game(id=game_uuid, folder_location="test/games", title="TestGame", status=GameStatus.WISHLIST, developer_id=None)
    db_session.add(game)
    db_session.commit()

    # Create Achievements linked to the game
    ach1 = Achievement(game_id=game_uuid, name="Bronze", description="Basic achievement.")
    ach2 = Achievement(game_id=game_uuid, name="Gold", description="Hardcore challenge.", is_secret=True)

    db_session.add_all([ach1, ach2])
    db_session.commit()

    # Test Retrieval and Count
    retrieved_game = db_session.get(Game, game_uuid)
    assert len(retrieved_game.achievements) == 2
    assert retrieved_game.achievements[1].name == "Gold"

def test_achievement_unique_constraints(db_session):
    """Tests that an achievement name/description combination should be unique per game."""
    # Setup Game
    game_uuid = uuid4()
    game = Game(id=game_uuid, folder_location="test/games", title="TestGame", status=GameStatus.WISHLIST, developer_id=None)
    db_session.add(game)
    db_session.commit()

    # Create first achievement
    ach1 = Achievement(game_id=game_uuid, name="UniqueAch", description="First time.")
    db_session.add(ach1)
    db_session.commit()

    # Attempt to create second achievement with the same name/description
    ach2 = Achievement(game_id=game_uuid, name="UniqueAch", description="First time.")
    with pytest.raises(Exception, match="UNIQUE constraint"):
        db_session.add(ach2)
        db_session.commit()