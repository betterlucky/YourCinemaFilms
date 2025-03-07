from django.db import migrations

class Migration(migrations.Migration):
    """
    Custom migration to ensure tables are created.
    This is a fallback in case normal migrations fail.
    """
    
    dependencies = [
        ('films_app', '0001_initial'),
    ]
    
    operations = [
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS "films_app_film" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "imdb_id" varchar(20) NOT NULL UNIQUE,
                "title" varchar(255) NOT NULL,
                "year" varchar(10) NOT NULL,
                "poster_url" varchar(500) NULL,
                "director" varchar(255) NULL,
                "plot" text NULL,
                "genres" varchar(255) NULL,
                "runtime" varchar(20) NULL,
                "actors" text NULL,
                "created_at" timestamp with time zone NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS "films_app_vote" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "created_at" timestamp with time zone NOT NULL,
                "film_id" bigint NOT NULL REFERENCES "films_app_film" ("id") DEFERRABLE INITIALLY DEFERRED,
                "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            
            CREATE TABLE IF NOT EXISTS "films_app_userprofile" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "birth_year" integer NULL,
                "gender" varchar(10) NULL,
                "country" varchar(100) NULL,
                "bio" text NULL,
                "privacy_level" varchar(20) NOT NULL,
                "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                "email_public" boolean NOT NULL,
                "email_verified" boolean NOT NULL,
                "profile_picture_url" varchar(500) NULL,
                "google_account_id" varchar(100) NULL
            );
            
            CREATE TABLE IF NOT EXISTS "films_app_genretag" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "tag" varchar(50) NOT NULL,
                "is_approved" boolean NOT NULL,
                "created_at" timestamp with time zone NOT NULL,
                "film_id" bigint NOT NULL REFERENCES "films_app_film" ("id") DEFERRABLE INITIALLY DEFERRED,
                "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            """,
            """
            DROP TABLE IF EXISTS "films_app_genretag";
            DROP TABLE IF EXISTS "films_app_userprofile";
            DROP TABLE IF EXISTS "films_app_vote";
            DROP TABLE IF EXISTS "films_app_film";
            """
        ),
    ] 