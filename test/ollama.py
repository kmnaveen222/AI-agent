data=[{'conversation_id': 61}, {'status': 'saved'}, {'messages': [['user', 'i want a briyani near guindy']]}, {'results': [{'restaurant': {'id': 2, 'name': 'Buhari', 'area': 'Guindy', 'city': 'Chennai', 'cuisine_tags': 'Biryani,North Indian', 'rating': 4.1, 'price_level': 2, 'is_open': 1}, 'menu': [{'id': 3, 'restaurant_id': 2, 'name': 'Chicken Biryani', 'description': 'Signature Buhari biryani', 'price_cents': 22000, 'is_available': 1, 'category': 'Main Course'}, {'id': 4, 'restaurant_id': 2, 'name': 'Egg Biryani', 'description': 'Fragrant rice with egg', 'price_cents': 18000, 'is_available': 1, 'category': 'Main Course'}]}]}, {'status': 'saved'}]


results = data[3].get("results", [])
print("Results:", results)