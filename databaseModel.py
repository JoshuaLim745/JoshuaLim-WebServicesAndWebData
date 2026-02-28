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
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

# Link between Users and their Favorite Genres
user_genre_link = Table(
    "user_genre_link",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
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
    
    #Add cascade to the many-to-many relationship
    fav_genres: Mapped[list["Genre"]] = relationship(
        secondary=user_genre_link,
        cascade="all, delete" 
    )

    #Explicitly define the relationship to ratings so they can be deleted
    ratings: Mapped[list["UserRatesBook"]] = relationship(
        cascade="all, delete-orphan"
    )

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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), primary_key=True)
    user_rating: Mapped[float] = mapped_column(Float)