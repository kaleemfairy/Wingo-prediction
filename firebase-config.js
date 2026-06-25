// Replace every REPLACE_* value with your Firebase project details.
// Firebase Console → Project Settings → Your apps → SDK setup and config
firebase.initializeApp({
  apiKey:            "REPLACE_API_KEY",
  authDomain:        "REPLACE_PROJECT_ID.firebaseapp.com",
  projectId:         "REPLACE_PROJECT_ID",
  storageBucket:     "REPLACE_PROJECT_ID.appspot.com",
  messagingSenderId: "REPLACE_SENDER_ID",
  appId:             "REPLACE_APP_ID"
});

const auth = firebase.auth();
const db   = firebase.firestore();
