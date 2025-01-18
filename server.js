require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const friendRoutes = require('./routes/friends');

const app = express();
const port = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Connect to MongoDB
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost/bible-app', {
  useNewUrlParser: true,
  useUnifiedTopology: true,
})
.then(() => console.log('Connected to MongoDB'))
.catch(err => console.error('Could not connect to MongoDB:', err));

// Mock authentication middleware (replace with your actual auth middleware)
app.use((req, res, next) => {
  // For testing purposes, set a mock user
  req.user = { id: '507f1f77bcf86cd799439011' }; // Replace with actual auth
  next();
});

// Routes
app.use('/api/friends', friendRoutes);

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
}); 