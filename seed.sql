-- seed.sql
INSERT INTO restaurants(name, area, city, cuisine_tags, rating, price_level, is_open) VALUES
('A2B (Adyar Ananda Bhavan)', 'T. Nagar', 'Chennai', 'South Indian,Sweets,Snacks', 4.3, 2, 1),
('Buhari', 'Guindy', 'Chennai', 'Biryani,North Indian', 4.1, 2, 1),
('Sangeetha Veg', 'Adyar', 'Chennai', 'South Indian,North Indian', 4.2, 2, 1);

INSERT INTO menu_items(restaurant_id, name, description, price_cents, is_available, category) VALUES
(1, 'Masala Dosa', 'Crispy dosa with potato masala', 12000, 1, 'Main Course'),
(1, 'Filter Coffee', 'Classic South Indian coffee', 4000, 1, 'Beverages'),
(2, 'Chicken Biryani', 'Signature Buhari biryani', 22000, 1, 'Main Course'),
(2, 'Egg Biryani', 'Fragrant rice with egg', 18000, 1, 'Main Course'),
(3, 'Meals', 'Complete South Indian thali', 16000, 1, 'Main Course');