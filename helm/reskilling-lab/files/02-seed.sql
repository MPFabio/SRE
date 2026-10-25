
INSERT INTO catalog.categories (id, name, description) VALUES
    (1, 'computers', 'Ordinateurs & Écrans'),
    (2, 'smartphones', 'Smartphones'),
    (3, 'audio', 'Audio'),
    (4, 'watches', 'Montres connectées'),
    (5, 'accessories', 'Accessoires')
ON CONFLICT (id) DO NOTHING;

INSERT INTO catalog.products (id, name, description, price, category, stock, image_url,
                              brand, compare_at_price, rating, rating_count) VALUES
    (1, 'MacBook Pro 16"', 'Puce M1 Pro, 16Go RAM, 512Go SSD', 2299.0, 'computers', 25, 'macbook', 'Apple', NULL, 4.8, 1247),
    (2, 'Laptop 13', 'AMD Ryzen 7 7840U, 32Go RAM, réparable et modulaire', 1399.0, 'computers', 18, 'laptop13', 'Framework', NULL, 4.6, 843),
    (3, 'Studio Display 27"', 'Écran 5K Retina, webcam 12MP, haut-parleurs', 1749.0, 'computers', 12, 'monitor', 'Apple', NULL, 4.4, 512),
    (4, 'iPhone 15 Pro', 'Titane, A17 Pro, 256Go', 1229.0, 'smartphones', 45, 'iphone', 'Apple', NULL, 4.7, 3182),
    (5, 'Pixel 8 Pro', 'Tensor G3, 12Go RAM, photo computationnelle', 1099.0, 'smartphones', 32, 'pixel', 'Google', 1299.0, 4.5, 1906),
    (6, 'Galaxy S24 Ultra', 'Snapdragon 8 Gen 3, S Pen, 200MP', 1419.0, 'smartphones', 28, 'samsung', 'Samsung', NULL, 4.6, 2471),
    (7, 'AirPods Pro 2', 'Réduction de bruit adaptative, USB-C', 279.0, 'audio', 85, 'airpods', 'Apple', 319.0, 4.7, 5630),
    (8, 'WH-1000XM3', 'Casque sans fil, ANC 30h d''autonomie', 249.0, 'audio', 42, 'sony', 'Sony', 299.0, 4.8, 4118),
    (9, 'One', 'Enceinte connectée, AirPlay 2 et commande vocale', 229.0, 'audio', 22, 'sonos', 'Sonos', NULL, 4.3, 687),
    (10, 'Apple Watch Ultra 2', 'GPS + Cellular, boîtier titane 49mm', 899.0, 'watches', 35, 'applewatch', 'Apple', NULL, 4.7, 1524),
    (11, 'Fenix 6X Pro Solar', 'Solaire, cartographie, 21 jours autonomie', 749.0, 'watches', 15, 'garmin', 'Garmin', 849.0, 4.6, 923),
    (12, 'Chargeur MagSafe', 'Charge sans fil 15W pour iPhone, USB-C', 49.0, 'accessories', 120, 'magsafe', 'Apple', NULL, 4.1, 2045),
    (13, 'MX Master 3S', 'Souris ergonomique, 8000 DPI, silencieuse', 119.0, 'accessories', 65, 'mxmaster', 'Logitech', 139.0, 4.9, 7382),
    (14, 'K4', 'Clavier mécanique 96% sans fil, Gateron Brown', 89.0, 'accessories', 38, 'keychron', 'Keychron', NULL, 4.5, 1163),
    (15, 'Thunderbolt 3 Dock', 'Dock 14 ports, charge 85W', 299.0, 'accessories', 20, 'dock', 'OWC', NULL, 4.4, 598)
ON CONFLICT (id) DO NOTHING;
