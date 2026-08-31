import pytest
from datetime import date, datetime
from uuid import UUID, uuid4

# Assuming we need to mock the database session and models for unit testing
# We will use a simple in-memory SQLite setup for this test file

def generate_developer_uuid():
    return str(uuid4())

@pytest.fixture
def db_session():
    """Mock SQLAlchemy Session fixture."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database.base import Base # Assuming Base is correctly imported/mocked
    
    # Use an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        yield db

# --- Test Developer Model ---

def test_developer_model_creation(db_session):
    """Test successful creation and saving of a new developer."""
    from src.backend.database.models import Developer # Adjust path if necessary
    
    # Create an instance (Mocking the UUID generation for predictability)
    test_id = "a" * 32
    developer = Developer(id=UUID(test_id), name="TestDev")
    db_session.add(developer)
    db_session.commit()
    
    # Test retrieval
    retrieved = db_session.query(Developer).get(developer.id)
    assert retrieved is not None
    assert retrieved.name == "TestDev"

def test_developer_unique_constraint(db_session):
    """Test that a developer name must be unique."""
    from src.backend.database.models import Developer
    
    # Create first user
    test_id = str(uuid4())
    dev1 = Developer(id=UUID(test_id), name="UniqueGuy")
    db_session.add(dev1)
    db_session.commit()

    # Try to create second user with the same name
    dev2 = Developer(id=UUID(str(uuid4())), name="UniqueGuy")
    with pytest.raises(Exception, match="unique constraint"): # Expecting a database integrity error
        db_session.add(dev2)
        db_session.commit()

# --- Placeholder for other models (if they exist and need testing) ---

def test_placeholder():
    """Placeholder for future tests."""
    assert True