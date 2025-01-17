Description :
This project is a multi-user (one admin/store manager and other users) app for buying grocery from a grocery store 
where admin can create and manage categories and products and other users (customers) can create account and log in to buy products from the shop.

Technologies used :
    1. Flask - for application code
    2. Jinja2 templates and Bootstrap for HTML generation and styling.
    3. SQLite and SQLAlchemy for data storage.

Architecture and Features :
a. The project is organized using the Model-View-Controller (MVC) architecture, with the controllers handling logic and routing,
   templates for displaying views, and models for interacting with the database.
b. Features implemented include :
  1. Admin(store manager) can login (using username and password which is set by developer).
  2. Admin dashboard
      • Manage category
          ✓ Add new category
          ✓ Edit category
          ✓ Delete category
          ✓ View products under category
          ✓ Search for category, product with different options like manufacture date, expiry date, price.
          • Manage products
          ✓ Add new product
          ✓ Edit product details
          ✓ Delete product
          ✓ Add quantity to product
          ✓ Search for category, product with different options like manufacture date, expiry date, price.
      • Logout admin.
  3. User (customer) can create account using username and password and login.
  4. User dashboard
        ✓ Search for category, product with different options like manufacture date, expiry date, price.
        ✓ Basic view of available products and categories.
        ✓ Add to cart & Buy
        ✓ See product details
        ✓ View cart
        ✓ Checkout
        ✓ View shopping history
        ✓ Logout
        ✓ Delete account
  5. Validation
        ✓ Server side validation with python, WT forms
        ✓ Client side validation with HTML
These features are implemented using functions created inside particular route for each functionality.
Demo video link: https://drive.google.com/file/d/1h5huvBgqwRsjeSpEAIiJFdziBejrhicQ/view?usp=sharing
