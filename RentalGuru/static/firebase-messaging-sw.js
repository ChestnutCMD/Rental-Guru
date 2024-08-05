// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBBecGpIXjG5gEdk7KbpxUd-kAZM0a_Hes",
  authDomain: "rental-guru-6ed62.firebaseapp.com",
  projectId: "rental-guru-6ed62",
  storageBucket: "rental-guru-6ed62.appspot.com",
  messagingSenderId: "120690662784",
  appId: "1:120690662784:web:bc8ab9e83770e472aeb565",
  measurementId: "G-7XY2SZNXZW"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);