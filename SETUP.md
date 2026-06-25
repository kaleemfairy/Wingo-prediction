# Firebase Setup Guide

Follow these steps once to connect the app to Firebase.

## 1. Create a Firebase Project

1. Go to https://console.firebase.google.com
2. Click **Add project** → give it a name → click through the steps
3. On the project dashboard, click **</>** (Web) to register a web app
4. Copy the `firebaseConfig` object shown

## 2. Fill in firebase-config.js

Open `firebase-config.js` and replace every `REPLACE_*` value with the values from step 1.

## 3. Enable Email/Password Auth

1. Firebase Console → **Authentication** → **Sign-in method**
2. Enable **Email/Password**

## 4. Create Firestore Database

1. Firebase Console → **Firestore Database** → **Create database**
2. Choose **Start in production mode**
3. Select a region → **Done**

## 5. Set Firestore Security Rules

In Firestore → **Rules**, paste:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow read, write: if request.auth != null && isAdmin();
    }
    function isAdmin() {
      return get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
  }
}
```

Click **Publish**.

## 6. Create Your Admin Account

1. Firebase Console → **Authentication** → **Users** → **Add user**
2. Enter your admin email + password → **Add user**
3. Copy the **User UID** shown in the list

## 7. Set Admin Role in Firestore

1. Firestore → **Data** → **Start collection**
2. Collection ID: `users`
3. Document ID: paste the UID from step 6
4. Add these fields:
   - `email` (string) → your admin email
   - `role` (string) → `admin`
   - `active` (boolean) → `true`
5. Click **Save**

## 8. Enable GitHub Pages

1. Repo → **Settings** → **Pages**
2. Branch: `claude/bdg-predictor-ui-hosting-4xjmiw` → folder: `/root`
3. Click **Save**

Your app will be live at `https://kaleemfairy.github.io/Wingo-prediction/`.
- **Login page**: `index.html` (default)
- **Admin panel**: `admin.html`
- **Predictor app**: `app.html` (customers land here after login)
