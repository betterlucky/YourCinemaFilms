# YourCinemaFilms - Feature Enhancement TODO List

This document outlines potential enhancements for the YourCinemaFilms platform, focused on helping users identify which films they'd actually attend in theaters.

## Core Functionality Enhancements

### 1. Cinema Preference Integration
- [x] Allow users to select their preferred cinema locations/chains
- [x] Add distance willing to travel for different types of films
- [ ] Enable notifications when a voted film is scheduled at their preferred cinema (PRIORITY INTEREST)

### 2. Screening Commitment Indicator
- [x] Add a "commitment level" to votes (e.g., "Definitely attending", "Interested", "Only if convenient")
- [x] Allow users to specify viewing preferences (IMAX, standard, 3D, etc.)
- [x] Implement a "bring friends" indicator to show social viewing interest

### 3. Theatrical Release Tracking
- [ ] Integrate with APIs to track upcoming theatrical releases
- [ ] Highlight films with theatrical release dates on user profiles
- [ ] Send notifications when voted films get theatrical release dates

## User Profile Improvements

### 4. Cinema Attendance History
- [ ] Track which voted films users actually attended in theaters
- [ ] Display a "cinema attendance rate" on profiles
- [ ] Offer insights on what factors influence actual attendance

### 5. Viewing Preference Section
- [ ] Add fields for preferred viewing times (weekday evenings, weekend matinees, etc.)
- [ ] Include price sensitivity indicators (full price, discount only, etc.)
- [ ] Allow users to specify special requirements (accessibility needs, subtitle preferences)

### 6. Local Cinema Integration
- [x] Display nearby cinemas on user profiles
- [ ] Show upcoming screenings of voted films at these locations
- [ ] Enable one-click ticket purchase links when available

## Community and Social Features

### 7. Group Cinema Outings
- [ ] Allow users to create cinema meetup events for specific films
- [ ] Enable group voting for which film to see together
- [ ] Implement a "looking for viewing companions" feature

### 8. Cinema-Specific Recommendations
- [ ] Suggest films that are "better on the big screen" based on cinematography, sound design, etc.
- [ ] Highlight limited theatrical releases that match user preferences
- [ ] Recommend films with strong community interest for group viewings

### 9. Film Revival Campaigns
- [ ] Enable users to campaign for older films to return to theaters
- [ ] Show aggregate interest in classic film screenings to cinema partners
- [ ] Facilitate special event screenings based on user demand

## Data and Analytics

### 10. Attendance Prediction Metrics
- [x] Develop algorithms to predict actual attendance based on vote patterns
- [ ] Show cinemas data on likely attendance for specific films
- [ ] Provide users with personalized "cinema worthiness" scores for films

### 11. Cinema Experience Ratings
- [ ] Allow users to rate their cinema experience after attending
- [ ] Track which types of films users prefer to see in theaters vs. at home
- [ ] Gather data on what enhances the cinema experience (premium formats, food options, etc.)

### 12. Seasonal Preference Tracking
- [ ] Analyze how weather, holidays, and seasons affect cinema attendance
- [ ] Show users their own patterns (e.g., "You attend 40% more films in winter")
- [ ] Help cinemas understand optimal scheduling for different film types

## Practical Features

### 13. Ticket Price Tracking
- [ ] Allow users to specify their price sensitivity for different films
- [ ] Track special offers and discount days at local cinemas
- [ ] Enable notifications for price drops or special deals

### 14. Viewing Party Coordination
- [ ] Facilitate coordination for groups attending the same screening
- [ ] Help with seat selection to keep groups together
- [ ] Provide tools for pre/post film meetups at nearby venues

### 15. Cinema Amenity Preferences
- [x] Track preferences for cinema amenities (reclining seats, food service, etc.)
- [ ] Match films with appropriate viewing experiences
- [ ] Help users find the optimal cinema experience for each film

## Business Integration

### 16. Cinema Partnership Features
- [ ] Create tools for cinemas to see aggregate demand for specific films
- [ ] Enable special promotions targeted at users who voted for specific films
- [ ] Develop a feedback loop between cinemas and potential audiences

### 17. Limited Release Demand Aggregation
- [ ] Help independent cinemas gauge interest in art house or limited release films
- [ ] Aggregate demand to help bring films to underserved areas
- [ ] Connect film distributors with data on regional interest

## Implementation Priority

Consider implementing these features in the following order:
1. ✅ Core functionality enhancements (1-3) - Partially implemented (Cinema preferences and commitment indicators)
2. User profile improvements (4-6)
3. Practical features (13-15)
4. Community and social features (7-9)
5. Data and analytics (10-12)
6. Business integration (16-17)

This prioritization focuses on enhancing the core user experience first, then building community features, and finally developing business partnerships. 

## Recently Implemented Features

### Cinema Preferences (March 2023)
- Added Cinema model to store information about cinema sites
- Created CinemaPreference model for users to select preferred cinemas
- Updated UserProfile to include travel distance preferences
- Removed the generic favorite_cinema field in favor of the more detailed model

### Commitment Indicators (March 2023)
- Enhanced Vote and CinemaVote models with commitment levels
- Added viewing format preferences (IMAX, 3D, etc.)
- Implemented social viewing preferences
- Added metrics to calculate and display commitment scores
- Maintained the original vote count for backward compatibility 