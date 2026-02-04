"""
Holds the database model and create it
"""
import pandas as pd
from sqlalchemy import create_engine, ForeignKey, String, Integer, Float, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

# 1. Connection Setup
DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5432/WebServicesDB"
engine = create_engine(DATABASE_URL)

class Base(DeclarativeBase):
    pass

# 2. THE LINKING TABLES (Association Tables)
# Link between Books and Genres
book_genre_link = Table(
    "book_genre_link",
    Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)

# Link between Users and their Favorite Genres
user_genre_link = Table(
    "user_genre_link",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)

# 3. THE CORE TABLES
class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    
    # Relationship: User <-> Favorite Genres
    fav_genres: Mapped[list["Genre"]] = relationship(secondary=user_genre_link)

class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Relationship: Book <-> Genres
    genres: Mapped[list["Genre"]] = relationship(secondary=book_genre_link)

class UserRatesBook(Base):
    __tablename__ = "user_rates_books"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), primary_key=True)
    user_rating: Mapped[float] = mapped_column(Float)

# Create all tables in PostgreSQL
Base.metadata.create_all(engine)

# 1. Load the CSV
df = pd.read_csv('filtered_google_books.csv')

# 2. Clean and get unique genres (handling the &amp; and comma splits)
all_genres = df['genre'].str.replace('&amp,', '&').str.split(',').explode().str.strip().unique()

with Session(engine) as session:
    for g_name in all_genres:
        if g_name and g_name.lower() != 'none':
            # Use the same 'check if exists' logic
            if not session.query(Genre).filter_by(name=g_name).first():
                session.add(Genre(name=g_name))
    
    session.commit()

# Assuming 'engine', 'User', and 'Genre' are already defined
with Session(engine) as session:
    # 1. Fetch or create genres first so we can link them
    # (Using 'get_one' or creating them if they don't exist)
    fantasy = session.query(Genre).filter_by(name="Fantasy").first() or Genre(name="Fantasy")
    manga = session.query(Genre).filter_by(name="Manga").first() or Genre(name="Manga")
    mystery = session.query(Genre).filter_by(name="Mystery & Detective").first() or Genre(name="Mystery & Detective")
    thriller = session.query(Genre).filter_by(name="Thrillers").first() or Genre(name="Thrillers")

    # 2. Generate 4 Users
    user1 = User(
        email="alice.j@example.com", password="hashed_password_1"
    )
    user1.fav_genres.extend([fantasy, mystery])

    user2 = User(
        email="bob.smith@example.com", password="hashed_password_2"
    )
    user2.fav_genres.extend([manga, thriller])

    user3 = User(
        email="charlie.d@example.com", password="hashed_password_3"
    )
    user3.fav_genres.extend([fantasy, manga])

    user4 = User(
        email="diana.p@example.com", password="hashed_password_4"
    )
    user4.fav_genres.extend([mystery, thriller])

    # 3. Add to session and commit
    session.add_all([user1, user2, user3, user4])
    session.commit()



def get_or_create_genre(session, name):
    """Helper to ensure we don't create duplicate genres."""
    name = name.strip().replace('&amp;', '&')
    if not name or name.lower() == 'none':
        return None
        
    genre = session.query(Genre).filter_by(name=name).first()
    if not genre:
        genre = Genre(name=name)
        session.add(genre)
        session.flush() # Flush to get the ID without committing yet
    return genre

# 2. Start the Data Injection
with Session(engine) as session:
    print("Starting data migration...")
    
    for _, row in df.iterrows():
        # Create the Book object
        # Note: We use the ID from the CSV as our Primary Key
        new_book = Book(
            id=row['ID'],
            title=row['title'],
            author=row['author'],
            avg_rating=row['rating'] if pd.notnull(row['rating']) else 0.0
        )
        
        # Handle Genres (The CSV has them as a string: "Fiction, Horror")
        genre_string = str(row['genre'])
        if genre_string and genre_string.lower() != 'none':
            # Split by comma and clean up each genre name
            genre_names = [g.strip() for g in genre_string.split(',')]
            
            for g_name in genre_names:
                genre_obj = get_or_create_genre(session, g_name)
                if genre_obj:
                    new_book.genres.append(genre_obj)
        
        session.add(new_book)

    # 3. Final Commit
    try:
        session.commit()
        print(f"Success! Inserted {len(df)} books into the 'books' table.")
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}")