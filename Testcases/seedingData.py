import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from databaseModel import Base, engine, Book, Genre, User # Import from your file

def reset_database():
    """Drops and recreates all tables defined in databaseModel.py"""
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database schema recreated successfully.")

def get_or_create_genre(session, name):
    """Helper to ensure we don't create duplicate genres."""
    name = name.strip()
    if not name or name.lower() == 'none':
        return None
        
    genre = session.query(Genre).filter_by(name=name).first()
    if not genre:
        genre = Genre(name=name)
        session.add(genre)
        session.flush() # Flush to get the ID without committing yet
    return genre

def run_migration():
    # 1. Load the CSV
    try:
        df = pd.read_csv('filtered_google_books.csv')
    except FileNotFoundError:
        print("Error: 'filtered_google_books.csv' not found.")
        return
    
    all_genres = df['genre'].str.replace('&amp,', '&').str.split(',').explode().str.strip().unique()

    # 2. Inject Data
    with Session(engine) as session:
        for g_name in all_genres:
            if g_name and g_name.lower() != 'none':
                # Use the same 'check if exists' logic
                if not session.query(Genre).filter_by(name=g_name).first():
                    session.add(Genre(name=g_name))
    
        session.commit()

    with Session(engine) as session:
        print("Starting data seeding...")
        
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


            
if __name__ == "__main__":
    reset_database()
    run_migration()