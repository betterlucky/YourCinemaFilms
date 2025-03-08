# YourCinemaFilms - Project Context

## Project Overview

YourCinemaFilms is a web platform designed to identify which films people would actually go to the cinema to watch. Unlike general film rating or recommendation platforms, our specific focus is on theatrical attendance - helping users discover films worth experiencing on the big screen and helping cinemas understand audience demand.

## Core Purpose

The primary purpose of YourCinemaFilms is to:

1. Allow users to vote for films they would genuinely attend in theaters
2. Aggregate this demand data to identify potential theatrical screenings
3. Connect film enthusiasts with theatrical opportunities to watch their desired films
4. Provide cinemas with actionable data about audience preferences

## Current Features

### User System
- User registration and authentication
- Extended user profiles with demographic information
- Privacy controls for profile information
- Social account integration (Google)
- Film voting system

### Film Database
- Film information from external APIs
- Film details including title, year, director, plot, genres
- Poster images and basic metadata
- Genre tagging system (including user-generated tags)

### Voting System
- Users can vote for films they want to see in theaters
- Vote tracking and display on user profiles
- Aggregated vote counts to show popularity

### Dashboard and Analytics
- Site activity statistics
- Genre distribution visualization
- Timeline of voting activity
- Top films by vote count
- Active user tracking

## Technical Stack

- **Backend**: Django (Python web framework)
- **Frontend**: HTML, CSS, JavaScript with Bootstrap
- **Database**: Django ORM (likely PostgreSQL)
- **Authentication**: Django authentication + social auth
- **Visualization**: Chart.js for data visualization

## Target Audience

1. **Film Enthusiasts**: People who appreciate the theatrical experience and actively seek films to watch in cinemas
2. **Cinema Operators**: Theaters looking to understand audience demand and optimize programming
3. **Film Distributors**: Companies seeking data on potential theatrical interest for their films
4. **Film Communities**: Groups interested in organizing screenings or cinema outings

## Business Model Potential

- **Data Services**: Providing aggregated, anonymized demand data to cinemas and distributors
- **Targeted Promotions**: Connecting cinemas with interested audiences for specific films
- **Special Screening Coordination**: Facilitating group bookings or special event screenings
- **Enhanced User Features**: Premium features for dedicated users

## Development Roadmap

The project is evolving from a basic voting platform to a comprehensive cinema attendance tool. Future development will focus on:

1. Enhancing the connection between online interest and actual theatrical attendance
2. Building community features around shared cinema experiences
3. Providing more detailed analytics on viewing preferences
4. Creating partnerships with cinemas and distributors

See the TODO.md file for specific planned enhancements.

## Project Values

- **Theatrical Experience**: We believe some films are meant to be seen on the big screen
- **Community**: Film viewing is often a social experience worth facilitating
- **Data Privacy**: User information is handled with appropriate privacy controls
- **Actionable Insights**: Data should lead to real-world screening opportunities

## Current Challenges

- Bridging the gap between online voting and actual attendance
- Building sufficient user base to provide meaningful aggregated data
- Establishing relationships with cinemas and distributors
- Creating features that enhance the theatrical film experience

This context document should be referenced when making design decisions or feature additions to ensure alignment with the core purpose of YourCinemaFilms. 