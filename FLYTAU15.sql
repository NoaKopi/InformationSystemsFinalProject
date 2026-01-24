

-- =========================================================
-- 1) Airports
-- =========================================================
CREATE TABLE Airports (
    Airport_ID INTEGER PRIMARY KEY,
    Airport_Name TEXT NOT NULL,
    City TEXT,
    Country TEXT
);

-- =========================================================
-- 2) Planes
-- =========================================================
CREATE TABLE Planes (
    Plane_ID INTEGER PRIMARY KEY,
    Purchase_Date TEXT,
    Plane_Size TEXT NOT NULL CHECK (Plane_Size IN ('SMALL','LARGE')),
    Manufacturer TEXT NOT NULL CHECK (Manufacturer IN ('Boeing','Airbus','Dassault'))
);

-- =========================================================
-- 3) Unidentified Guests
-- =========================================================
CREATE TABLE Unidentified_Guests (
    Email_Address TEXT PRIMARY KEY,
    First_Name_In_English TEXT,
    Last_Name_In_English TEXT
);

-- =========================================================
-- 4) Registered Clients
-- =========================================================
CREATE TABLE Registered_Clients (
    Passport_ID TEXT PRIMARY KEY,
    Registered_Clients_Email_Address TEXT UNIQUE NOT NULL,
    First_Name_In_English TEXT,
    Last_Name_In_English TEXT,
    Date_Of_Birth TEXT,
    Client_Password TEXT,
    Registration_Date TEXT DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 5) Workers
-- =========================================================
CREATE TABLE Pilots (
    Worker_ID INTEGER PRIMARY KEY,
    City TEXT,
    Street TEXT,
    House_Number INTEGER,
    First_Name_In_Hebrew TEXT,
    Last_Name_In_Hebrew TEXT,
    Worker_Phone_Number TEXT,
    Start_Date TEXT,
    Is_Qualified INTEGER CHECK (Is_Qualified IN (0,1))
);

CREATE TABLE Flight_Attendants (
    Worker_ID INTEGER PRIMARY KEY,
    City TEXT,
    Street TEXT,
    House_Number INTEGER,
    First_Name_In_Hebrew TEXT,
    Last_Name_In_Hebrew TEXT,
    Worker_Phone_Number TEXT,
    Start_Date TEXT,
    Is_Qualified INTEGER CHECK (Is_Qualified IN (0,1))
);

CREATE TABLE Managers (
    Worker_ID INTEGER PRIMARY KEY,
    City TEXT,
    Street TEXT,
    House_Number INTEGER,
    First_Name_In_Hebrew TEXT,
    Last_Name_In_Hebrew TEXT,
    Worker_Phone_Number TEXT,
    Start_Date TEXT,
    Manager_Password TEXT,
    Manager_First_Name_In_English TEXT,
    Manager_Last_Name_In_English TEXT
);

-- =========================================================
-- 6) Routes
-- =========================================================
CREATE TABLE Routes (
    Origin_Airport INTEGER,
    Destination_Airport INTEGER,
    Duration TEXT,
    PRIMARY KEY (Origin_Airport, Destination_Airport),
    FOREIGN KEY (Origin_Airport) REFERENCES Airports(Airport_ID),
    FOREIGN KEY (Destination_Airport) REFERENCES Airports(Airport_ID)
);

-- =========================================================
-- 7) Flight
-- =========================================================
CREATE TABLE Flight (
    Flight_ID INTEGER PRIMARY KEY,
    Plane_ID INTEGER NOT NULL,
    Origin_Airport INTEGER NOT NULL,
    Destination_Airport INTEGER NOT NULL,
    Departure_Time TEXT NOT NULL,
    Departure_Date TEXT NOT NULL,
    Economy_Price REAL NOT NULL,
    Business_Price REAL NOT NULL,
    Flight_Status TEXT NOT NULL DEFAULT 'active'
        CHECK (Flight_Status IN ('active','cancelled','done','full')),
    FOREIGN KEY (Plane_ID) REFERENCES Planes(Plane_ID),
    FOREIGN KEY (Origin_Airport) REFERENCES Airports(Airport_ID),
    FOREIGN KEY (Destination_Airport) REFERENCES Airports(Airport_ID)
);

-- =========================================================
-- 8) Orders
-- =========================================================
CREATE TABLE Orders (
    Unique_Order_ID INTEGER PRIMARY KEY,
    Flight_ID INTEGER NOT NULL,
    Registered_Clients_Email_Address TEXT NULL,
    Unidentified_Guest_Email_Address TEXT NULL,
    Date_Of_Order TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Order_Status TEXT NOT NULL DEFAULT 'active'
        CHECK (Order_Status IN ('active','done','systemcancellation','customercancellation')),
    Final_Total REAL NOT NULL DEFAULT 0.00,
    FOREIGN KEY (Flight_ID) REFERENCES Flight(Flight_ID),
    FOREIGN KEY (Registered_Clients_Email_Address)
        REFERENCES Registered_Clients(Registered_Clients_Email_Address),
    FOREIGN KEY (Unidentified_Guest_Email_Address)
        REFERENCES Unidentified_Guests(Email_Address),
    CONSTRAINT chk_one_customer CHECK (
        (Registered_Clients_Email_Address IS NOT NULL AND Unidentified_Guest_Email_Address IS NULL)
        OR
        (Registered_Clients_Email_Address IS NULL AND Unidentified_Guest_Email_Address IS NOT NULL)
    )
);

-- =========================================================
-- 9) Seats
-- =========================================================
CREATE TABLE Seats (
    Plane_ID INTEGER,
    Column_Number TEXT,
    Row_Num INTEGER,
    Class TEXT NOT NULL CHECK (Class IN ('Economy','Business')),
    PRIMARY KEY (Plane_ID, Column_Number, Row_Num),
    FOREIGN KEY (Plane_ID) REFERENCES Planes(Plane_ID)
);

-- =========================================================
-- 10) Selected_Seats
-- =========================================================
CREATE TABLE Selected_Seats (
    Plane_ID INTEGER,
    Unique_Order_ID INTEGER,
    Column_Number TEXT,
    Row_Num INTEGER,
    Is_Occupied INTEGER DEFAULT 1 CHECK (Is_Occupied IN (0,1)),
    PRIMARY KEY (Plane_ID, Unique_Order_ID, Column_Number, Row_Num),
    FOREIGN KEY (Plane_ID) REFERENCES Planes(Plane_ID),
    FOREIGN KEY (Unique_Order_ID) REFERENCES Orders(Unique_Order_ID),
    FOREIGN KEY (Plane_ID, Column_Number, Row_Num)
        REFERENCES Seats(Plane_ID, Column_Number, Row_Num)
);

-- =========================================================
-- 11) Phone Numbers
-- =========================================================
CREATE TABLE Registered_Clients_Phone_Numbers (
    Passport_ID TEXT,
    Phone_Numbers TEXT,
    PRIMARY KEY (Passport_ID, Phone_Numbers),
    FOREIGN KEY (Passport_ID) REFERENCES Registered_Clients(Passport_ID)
);

CREATE TABLE Unidentified_Guests_Phone_Numbers (
    Unidentified_Guest_Email_Address TEXT,
    Phone_Numbers TEXT,
    PRIMARY KEY (Unidentified_Guest_Email_Address, Phone_Numbers),
    FOREIGN KEY (Unidentified_Guest_Email_Address)
        REFERENCES Unidentified_Guests(Email_Address)
);

-- =========================================================
-- 12) Workers assigned to flights
-- =========================================================
CREATE TABLE Pilots_Scheduled_to_Flights (
    Worker_ID INTEGER,
    Flight_ID INTEGER,
    PRIMARY KEY (Worker_ID, Flight_ID),
    FOREIGN KEY (Worker_ID) REFERENCES Pilots(Worker_ID),
    FOREIGN KEY (Flight_ID) REFERENCES Flight(Flight_ID)
);

CREATE TABLE Flight_Attendants_Assigned_To_Flights (
    Worker_ID INTEGER,
    Flight_ID INTEGER,
    PRIMARY KEY (Worker_ID, Flight_ID),
    FOREIGN KEY (Worker_ID) REFERENCES Flight_Attendants(Worker_ID),
    FOREIGN KEY (Flight_ID) REFERENCES Flight(Flight_ID)
);

-- =========================================================
-- 13) Has_an_order
-- =========================================================
CREATE TABLE Has_an_order (
    Email_Address TEXT,
    Unique_Order_ID INTEGER,
    Quantity_of_tickets INTEGER NOT NULL,
    PRIMARY KEY (Email_Address, Unique_Order_ID),
    FOREIGN KEY (Unique_Order_ID) REFERENCES Orders(Unique_Order_ID)
);

-- =========================================================
-- 14) Defines
-- =========================================================
CREATE TABLE Defines (
    Origin_Airport INTEGER,
    Destination_Airport INTEGER,
    Airport_ID INTEGER,
    PRIMARY KEY (Origin_Airport, Destination_Airport, Airport_ID),
    FOREIGN KEY (Origin_Airport) REFERENCES Airports(Airport_ID),
    FOREIGN KEY (Destination_Airport) REFERENCES Airports(Airport_ID),
    FOREIGN KEY (Airport_ID) REFERENCES Airports(Airport_ID)
);

-- =========================================================
-- INSERTS
-- =========================================================

-- Airports (20)
INSERT INTO Airports (Airport_ID, Airport_Name, City, Country) VALUES
(1,'Ben Gurion Airport','Tel Aviv','Israel'),
(2,'John F. Kennedy International Airport','New York','United States'),
(3,'Heathrow Airport','London','United Kingdom'),
(4,'Charles de Gaulle Airport','Paris','France'),
(5,'Frankfurt Airport','Frankfurt','Germany'),
(6,'Amsterdam Airport Schiphol','Amsterdam','Netherlands'),
(7,'Madrid-Barajas Airport','Madrid','Spain'),
(8,'Barcelona-El Prat Airport','Barcelona','Spain'),
(9,'Dubai International Airport','Dubai','United Arab Emirates'),
(10,'Istanbul Airport','Istanbul','Turkey'),
(11,'Rome Fiumicino Airport','Rome','Italy'),
(12,'Zurich Airport','Zurich','Switzerland'),
(13,'Vienna International Airport','Vienna','Austria'),
(14,'Athens International Airport','Athens','Greece'),
(15,'Cairo International Airport','Cairo','Egypt'),
(16,'Toronto Pearson International Airport','Toronto','Canada'),
(17,'Los Angeles International Airport','Los Angeles','United States'),
(18,'Singapore Changi Airport','Singapore','Singapore'),
(19,'Hong Kong International Airport','Hong Kong','China'),
(20,'Narita International Airport','Tokyo','Japan');

-- Planes
INSERT INTO Planes (Plane_ID, Purchase_Date, Plane_Size, Manufacturer) VALUES
(101,'2016-03-12','SMALL','Boeing'),
(102,'2017-08-25','LARGE','Airbus'),
(103,'2018-01-10','SMALL','Dassault'),
(104,'2019-11-05','LARGE','Boeing'),
(105,'2020-06-14','LARGE','Airbus'),
(106,'2021-02-19','LARGE','Boeing'),
(107,'2015-09-30','SMALL','Airbus'),
(108,'2014-12-22','SMALL','Dassault'),
(109,'2013-07-18','LARGE','Boeing'),
(110,'2012-05-09','LARGE','Airbus');

-- Routes (seed)
INSERT INTO Routes (Origin_Airport, Destination_Airport, Duration) VALUES
(1,3,'05:10:00'),
(1,4,'04:55:00'),
(1,9,'03:20:00'),
(2,3,'07:05:00'),
(3,4,'01:15:00'),
(3,5,'01:40:00'),
(9,18,'07:30:00'),
(18,19,'03:55:00'),
(19,20,'04:30:00'),
(15,1,'02:10:00');

-- fill missing routes with 00:00:00
INSERT INTO Routes (Origin_Airport, Destination_Airport, Duration)
SELECT
  a1.Airport_ID,
  a2.Airport_ID,
  '00:00:00'
FROM Airports a1
JOIN Airports a2
  ON a1.Airport_ID <> a2.Airport_ID
LEFT JOIN Routes r
  ON r.Origin_Airport = a1.Airport_ID
 AND r.Destination_Airport = a2.Airport_ID
WHERE r.Origin_Airport IS NULL;

-- SQLite: rewrite UPDATE...JOIN using a CTE + correlated update
WITH rc AS (
  SELECT
    rowid AS rid,
    (SELECT Country FROM Airports WHERE Airport_ID = Origin_Airport)      AS oc,
    (SELECT Country FROM Airports WHERE Airport_ID = Destination_Airport) AS dc
  FROM Routes
)
UPDATE Routes
SET Duration = (
  SELECT
    CASE
      WHEN oc = dc THEN '01:00:00'
      WHEN oc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece')
       AND dc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece')
        THEN '02:15:00'
      WHEN oc IN ('Israel','United Arab Emirates','Turkey','Egypt')
       AND dc IN ('Israel','United Arab Emirates','Turkey','Egypt')
        THEN '03:00:00'
      WHEN oc IN ('China','Japan','Singapore')
       AND dc IN ('China','Japan','Singapore')
        THEN '04:30:00'
      WHEN oc IN ('United States','Canada')
       AND dc IN ('United States','Canada')
        THEN '05:00:00'
      WHEN (oc IN ('Israel','United Arab Emirates','Turkey','Egypt')
        AND dc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece'))
        OR (dc IN ('Israel','United Arab Emirates','Turkey','Egypt')
        AND oc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece'))
        THEN '04:00:00'
      WHEN (oc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece')
        AND dc IN ('United States','Canada'))
        OR (dc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece')
        AND oc IN ('United States','Canada'))
        THEN '08:45:00'
      WHEN (oc IN ('Israel','United Arab Emirates','Turkey','Egypt')
        AND dc IN ('United States','Canada'))
        OR (dc IN ('Israel','United Arab Emirates','Turkey','Egypt')
        AND oc IN ('United States','Canada'))
        THEN '12:00:00'
      WHEN (oc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece')
        AND dc IN ('China','Japan','Singapore'))
        OR (dc IN ('United Kingdom','France','Germany','Netherlands','Spain','Italy','Switzerland','Austria','Greece')
        AND oc IN ('China','Japan','Singapore'))
        THEN '11:30:00'
      WHEN (oc IN ('Israel','United Arab Emirates','Turkey','Egypt')
        AND dc IN ('China','Japan','Singapore'))
        OR (dc IN ('Israel','United Arab Emirates','Turkey','Egypt')
        AND oc IN ('China','Japan','Singapore'))
        THEN '13:00:00'
      ELSE '06:00:00'
    END
  FROM rc
  WHERE rc.rid = Routes.rowid
);

-- Defines (seed)
INSERT INTO Defines (Origin_Airport, Destination_Airport, Airport_ID) VALUES
(1,3,1),
(1,4,1),
(1,9,1),
(2,3,2),
(3,4,3),
(3,5,3),
(9,18,9),
(18,19,18),
(19,20,19),
(15,1,15);

-- fill missing defines
INSERT INTO Defines (Origin_Airport, Destination_Airport, Airport_ID)
SELECT
  r.Origin_Airport,
  r.Destination_Airport,
  r.Origin_Airport
FROM Routes r
LEFT JOIN Defines d
  ON d.Origin_Airport = r.Origin_Airport
 AND d.Destination_Airport = r.Destination_Airport
 AND d.Airport_ID = r.Origin_Airport
WHERE d.Origin_Airport IS NULL;

-- Guests
INSERT INTO Unidentified_Guests (Email_Address, First_Name_In_English, Last_Name_In_English) VALUES
('guest01@mail.com','Ava','Brooks'),
('guest02@mail.com','Noah','Reed'),
('guest03@mail.com','Mia','Turner'),
('guest04@mail.com','Liam','Parker'),
('guest05@mail.com','Zoe','Campbell'),
('guest06@mail.com','Ethan','Morgan'),
('guest07@mail.com','Lily','Scott'),
('guest08@mail.com','Lucas','Bennett'),
('guest09@mail.com','Emma','Collins'),
('guest10@mail.com','Oliver','Ward');

-- Registered clients
INSERT INTO Registered_Clients
(Registered_Clients_Email_Address, Passport_ID, First_Name_In_English, Last_Name_In_English, Date_Of_Birth, Client_Password, Registration_Date) VALUES
('alice.kim@mail.com','P100001','Alice','Kim','1997-02-14','hash_a1','2025-01-05 10:10:10'),
('john.smith@mail.com','P100002','John','Smith','1990-06-20','hash_a2','2025-01-06 11:11:11'),
('sara.lee@mail.com','P100003','Sara','Lee','1988-12-03','hash_a3','2025-01-07 09:05:30'),
('david.ng@mail.com','P100004','David','Ng','1995-04-27','hash_a4','2025-01-10 14:20:00'),
('nina.patel@mail.com','P100005','Nina','Patel','1999-09-19','hash_a5','2025-01-12 16:40:12'),
('mark.brown@mail.com','P100006','Mark','Brown','1985-03-01','hash_a6','2025-02-02 08:00:00'),
('laura.diaz@mail.com','P100007','Laura','Diaz','1992-08-08','hash_a7','2025-02-15 13:30:00'),
('yousef.hassan@mail.com','P100008','Yousef','Hassan','1987-11-11','hash_a8','2025-03-01 17:17:17'),
('emily.wang@mail.com','P100009','Emily','Wang','2000-01-29','hash_a9','2025-03-09 12:00:00'),
('robert.jones@mail.com','P100010','Robert','Jones','1993-05-06','hash_b1','2025-03-20 18:05:00');

INSERT INTO Registered_Clients_Phone_Numbers (Passport_ID, Phone_Numbers) VALUES
('P100001','+972-50-1111111'),
('P100002','+1-212-555-0101'),
('P100003','+33-6-12-34-56-78'),
('P100004','+44-7700-900123'),
('P100005','+91-98765-43210');

INSERT INTO Unidentified_Guests_Phone_Numbers (Unidentified_Guest_Email_Address, Phone_Numbers) VALUES
('guest01@mail.com','+1-917-555-0001'),
('guest02@mail.com','+44-7700-900222'),
('guest03@mail.com','+33-6-98-76-54-32'),
('guest04@mail.com','+49-160-111-2222'),
('guest05@mail.com','+34-611-222-333');

-- =========================================================
-- SEATS  (TEMP tables are supported in SQLite)
-- =========================================================
DROP TABLE IF EXISTS tmp_numbers;
CREATE TEMP TABLE tmp_numbers (n INTEGER PRIMARY KEY);

INSERT INTO tmp_numbers (n) VALUES
(1),(2),(3),(4),(5),
(6),(7),(8),(9),(10),
(11),(12),(13),(14),(15),
(16),(17),(18),(19),(20),
(21),(22),(23),(24),(25);

INSERT INTO Seats (Plane_ID, Column_Number, Row_Num, Class)
SELECT
    p.Plane_ID,
    c.col,
    t.n,
    CASE
        WHEN p.Plane_ID IN (102,104,105,106,109,110) AND t.n <= 5 THEN 'Business'
        ELSE 'Economy'
    END
FROM Planes p
JOIN tmp_numbers t
JOIN (
    SELECT 'A' AS col
    UNION ALL SELECT 'B'
    UNION ALL SELECT 'C'
    UNION ALL SELECT 'D'
) c;

UPDATE Planes
SET Plane_Size =
  CASE
    WHEN EXISTS (
      SELECT 1 FROM Seats s
      WHERE s.Plane_ID = Planes.Plane_ID
        AND s.Class = 'Business'
    ) THEN 'LARGE'
    ELSE 'SMALL'
  END;

-- =========================================================
-- FLIGHTS
-- =========================================================
INSERT INTO Flight
(Flight_ID, Plane_ID, Origin_Airport, Destination_Airport, Departure_Time, Departure_Date, Economy_Price, Business_Price, Flight_Status) VALUES
(5001,101,1,3,'08:00:00','2026-01-20',320.00,990.00,'active'),
(5002,102,1,3,'14:30:00','2026-01-20',335.00,1040.00,'active'),
(5003,103,1,3,'21:15:00','2026-01-20',300.00,950.00,'active'),
(5004,104,1,3,'09:10:00','2026-01-22',340.00,1060.00,'cancelled'),
(5005,105,1,3,'18:45:00','2026-01-23',310.00,970.00,'active'),

(5006,106,1,4,'08:00:00','2026-01-21',280.00,920.00,'active'),
(5007,107,1,4,'14:30:00','2026-01-21',295.00,980.00,'active'),
(5008,108,1,4,'21:15:00','2026-01-21',270.00,890.00,'done'),
(5009,109,1,4,'10:20:00','2026-01-24',305.00,1005.00,'active'),
(5010,110,1,4,'19:05:00','2026-01-25',275.00,910.00,'active'),

(5011,101,1,9,'08:00:00','2026-01-22',210.00,780.00,'active'),
(5012,102,1,9,'14:30:00','2026-01-22',225.00,820.00,'active'),
(5013,103,1,9,'21:15:00','2026-01-22',200.00,740.00,'active'),
(5014,104,1,9,'11:30:00','2026-01-26',235.00,850.00,'cancelled'),
(5015,105,1,9,'20:10:00','2026-01-27',205.00,760.00,'active'),

(5016,106,2,3,'08:00:00','2026-01-23',410.00,1350.00,'active'),
(5017,102,2,3,'14:30:00','2026-01-23',420.00,1380.00,'active'),
(5018,105,2,3,'21:15:00','2026-01-23',395.00,1290.00,'active'),
(5019,109,2,3,'12:15:00','2026-01-28',430.00,1420.00,'done'),
(5020,110,2,3,'19:50:00','2026-01-29',405.00,1335.00,'active'),

(5021,101,3,4,'08:00:00','2026-01-24',120.00,420.00,'active'),
(5022,102,3,4,'14:30:00','2026-01-24',130.00,450.00,'active'),
(5023,103,3,4,'21:15:00','2026-01-24',110.00,390.00,'active'),
(5024,104,3,4,'09:40:00','2026-01-30',135.00,465.00,'active'),
(5025,105,3,4,'18:20:00','2026-01-31',115.00,405.00,'cancelled'),

(5026,106,3,5,'08:00:00','2026-01-25',140.00,470.00,'active'),
(5027,107,3,5,'14:30:00','2026-01-25',150.00,500.00,'active'),
(5028,108,3,5,'21:15:00','2026-01-25',135.00,455.00,'active'),
(5029,109,3,5,'10:55:00','2026-02-01',155.00,515.00,'done'),
(5030,110,3,5,'19:35:00','2026-02-02',145.00,485.00,'active'),

(5031,110,9,18,'08:00:00','2026-01-26',520.00,1650.00,'active'),
(5032,102,9,18,'14:30:00','2026-01-26',545.00,1720.00,'active'),
(5033,106,9,18,'21:15:00','2026-01-26',500.00,1580.00,'active'),
(5034,104,9,18,'12:05:00','2026-02-03',555.00,1750.00,'active'),
(5035,105,9,18,'20:40:00','2026-02-04',510.00,1620.00,'cancelled'),

(5036,106,18,19,'08:00:00','2026-01-27',260.00,900.00,'active'),
(5037,107,18,19,'14:30:00','2026-01-27',275.00,940.00,'active'),
(5038,108,18,19,'21:15:00','2026-01-27',250.00,860.00,'done'),
(5039,109,18,19,'11:10:00','2026-02-05',285.00,970.00,'active'),
(5040,110,18,19,'19:25:00','2026-02-06',255.00,880.00,'active'),

(5041,101,19,20,'08:00:00','2026-01-28',300.00,980.00,'active'),
(5042,102,19,20,'14:30:00','2026-01-28',315.00,1030.00,'active'),
(5043,103,19,20,'21:15:00','2026-01-28',290.00,950.00,'active'),
(5044,104,19,20,'12:35:00','2026-02-07',320.00,1060.00,'active'),
(5045,105,19,20,'20:55:00','2026-02-08',295.00,960.00,'cancelled'),

(5046,106,15,1,'08:00:00','2026-01-29',160.00,520.00,'active'),
(5047,107,15,1,'14:30:00','2026-01-29',170.00,560.00,'active'),
(5048,108,15,1,'21:15:00','2026-01-29',155.00,500.00,'active'),
(5049,109,15,1,'10:00:00','2026-02-09',175.00,570.00,'done'),
(5050,110,15,1,'19:15:00','2026-02-10',165.00,540.00,'active');

-- =========================================================
-- ORDERS
-- =========================================================
INSERT INTO Orders
(Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address, Order_Status) VALUES
(9001,5001,'alice.kim@mail.com',NULL,'active'),
(9002,5001,'john.smith@mail.com',NULL,'active'),
(9003,5002,'sara.lee@mail.com',NULL,'customercancellation'),
(9004,5006,'david.ng@mail.com',NULL,'active'),
(9005,5011,NULL,'guest01@mail.com','active'),
(9006,5012,NULL,'guest02@mail.com','active'),
(9007,5016,'nina.patel@mail.com',NULL,'active'),
(9008,5019,'mark.brown@mail.com',NULL,'systemcancellation'),
(9009,5021,NULL,'guest03@mail.com','active'),
(9010,5022,'laura.diaz@mail.com',NULL,'active');

-- Has_an_order
INSERT INTO Has_an_order (Email_Address, Unique_Order_ID, Quantity_of_tickets) VALUES
('alice.kim@mail.com',9001,2),
('john.smith@mail.com',9002,1),
('sara.lee@mail.com',9003,3),
('david.ng@mail.com',9004,1),
('guest01@mail.com',9005,2),
('guest02@mail.com',9006,4),
('nina.patel@mail.com',9007,2),
('mark.brown@mail.com',9008,1),
('guest03@mail.com',9009,2),
('laura.diaz@mail.com',9010,5);

-- Selected_Seats (BOOLEAN -> 0/1)
INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied) VALUES
(101,9001,'A',1,1),
(101,9001,'B',1,1),
(101,9002,'C',2,1),
(106,9004,'A',6,1),
(101,9005,'D',3,1),
(102,9006,'A',10,1),
(106,9007,'B',4,1),
(109,9008,'A',1,1),
(101,9009,'C',7,1),
(102,9010,'D',5,1);

-- Managers
INSERT INTO Managers
(Worker_ID, City, Street, House_Number,
 First_Name_In_Hebrew, Last_Name_In_Hebrew,
 Worker_Phone_Number, Start_Date,
 Manager_Password, Manager_First_Name_In_English, Manager_Last_Name_In_English)
VALUES
(7001, 'Tel Aviv', 'Ibn Gabirol', 10, 'מיכל', 'קופילוביץ', '050-1234567', '2024-01-01', 'admin123', 'Michal', 'Admin'),
(7002, 'Jerusalem', 'Jaffa', 25, 'נועה', 'כהן', '052-7654321', '2024-02-15', 'admin123', 'Noa', 'Admin');

-- Pilots
INSERT INTO Pilots
(Worker_ID, City, Street, House_Number, First_Name_In_Hebrew, Last_Name_In_Hebrew,
 Worker_Phone_Number, Start_Date, Is_Qualified)
VALUES
(3001,'Tel Aviv','Dizengoff',10,'דני','לוי','050-3001001','2022-01-10',1),
(3002,'Tel Aviv','Ibn Gabirol',22,'אור','כהן','050-3001002','2021-06-05',1),
(3003,'Jerusalem','King George',7,'טל','מזרחי','050-3001003','2020-03-18',1),
(3004,'Haifa','Hatzionut',14,'נועם','פרץ','050-3001004','2019-11-01',1),
(3005,'Rishon LeZion','Herzl',5,'שחר','אלון','050-3001005','2023-02-12',1),
(3006,'Netanya','Sokolov',9,'מיכאל','שפירא','050-3001006','2024-04-01',1),
(3011,'Tel Aviv','Ben Yehuda',3,'דוד','ברק','050-3001011','2023-09-20',0),
(3012,'Jerusalem','Jaffa',40,'רון','שחם','050-3001012','2022-07-15',0),
(3013,'Haifa','Hanasi',18,'עידו','דגן','050-3001013','2024-01-05',0),
(3014,'Petah Tikva','Haim Ozer',11,'אלעד','קציר','050-3001014','2021-12-28',0);

-- Flight Attendants
INSERT INTO Flight_Attendants
(Worker_ID, City, Street, House_Number, First_Name_In_Hebrew, Last_Name_In_Hebrew,
 Worker_Phone_Number, Start_Date, Is_Qualified)
VALUES
(4001,'Tel Aviv','Arlozorov',12,'נועה','לוי','050-4001001','2022-02-01',1),
(4002,'Tel Aviv','Weizmann',8,'ליה','כהן','050-4001002','2021-05-10',1),
(4003,'Jerusalem','Agripas',25,'אייל','דוידי','050-4001003','2020-08-19',1),
(4004,'Haifa','Moriah',30,'דנה','ברק','050-4001004','2019-03-03',1),
(4005,'Ramat Gan','Bialik',6,'שני','פרידמן','050-4001005','2023-01-12',1),
(4006,'Holon','Sderot Yerushalayim',55,'מאיה','לינדר','050-4001006','2024-06-20',1),
(4007,'Netanya','Shderot Chen',4,'יעל','שחר','050-4001007','2022-09-09',1),
(4008,'Ashdod','HaAtzmaut',16,'עדי','אורן','050-4001008','2021-11-11',1),
(4009,'Beer Sheva','Rager',9,'לירון','ממן','050-4001009','2020-12-30',1),
(4010,'Petah Tikva','Rothschild',2,'הילה','דרור','050-4001010','2023-05-05',1),
(4011,'Tel Aviv','Allenby',1,'אלמוג','רם','050-4001011','2024-02-14',0),
(4012,'Jerusalem','Hillel',13,'שקד','גבע','050-4001012','2022-10-02',0),
(4013,'Haifa','Herzl',27,'תמר','סגל','050-4001013','2023-08-08',0),
(4014,'Rishon LeZion','Remez',19,'בר','שלו','050-4001014','2021-04-17',0),
(4015,'Netanya','Pinsker',5,'יובל','לביא','050-4001015','2020-01-01',0);

-- =========================================================
-- Recalculate Final_Total (SQLite-compatible: no UPDATE...JOIN)
-- =========================================================
DROP TABLE IF EXISTS tmp_order_totals;
CREATE TEMP TABLE tmp_order_totals AS
SELECT
    o.Unique_Order_ID,
    ROUND(SUM(
        CASE
            WHEN s.Class = 'Business' THEN f.Business_Price
            ELSE f.Economy_Price
        END
    ), 2) AS seats_total
FROM Orders o
JOIN Flight f ON f.Flight_ID = o.Flight_ID
JOIN Selected_Seats ss ON ss.Unique_Order_ID = o.Unique_Order_ID AND ss.Is_Occupied = 1
JOIN Seats s
  ON s.Plane_ID = ss.Plane_ID
 AND s.Row_Num = ss.Row_Num
 AND s.Column_Number = ss.Column_Number
GROUP BY o.Unique_Order_ID;

UPDATE Orders
SET Final_Total =
    CASE
        WHEN Order_Status = 'systemcancellation' THEN 0.00
        WHEN Order_Status = 'customercancellation' THEN ROUND(COALESCE((SELECT seats_total FROM tmp_order_totals t WHERE t.Unique_Order_ID = Orders.Unique_Order_ID), 0.00) * 0.05, 2)
        ELSE COALESCE((SELECT seats_total FROM tmp_order_totals t WHERE t.Unique_Order_ID = Orders.Unique_Order_ID), 0.00)
    END;

-- =========================================================
-- EXTRA DONE FLIGHTS + ORDERS + SEATS (as you had)
-- =========================================================
INSERT INTO Flight
(Flight_ID, Plane_ID, Origin_Airport, Destination_Airport, Departure_Time, Departure_Date, Economy_Price, Business_Price, Flight_Status)
VALUES
(6001,108,1,4,'09:00:00','2025-12-05',260.00,860.00,'done'),
(6002,101,1,3,'13:30:00','2025-12-10',310.00,980.00,'done'),
(6003,109,2,3,'08:15:00','2025-12-15',420.00,1400.00,'done'),
(6004,106,3,5,'16:40:00','2025-12-20',150.00,520.00,'done'),
(6005,108,18,19,'21:10:00','2025-12-28',240.00,820.00,'done'),
(6006,109,1,9,'07:45:00','2026-01-03',230.00,840.00,'done'),
(6007,106,15,1,'12:05:00','2026-01-08',170.00,560.00,'done'),
(6008,101,3,4,'18:25:00','2026-01-12',125.00,430.00,'done'),
(6009,108,1,4,'10:10:00','2026-01-18',265.00,870.00,'done'),
(6010,109,19,20,'20:00:00','2026-01-27',305.00,990.00,'done');

INSERT INTO Orders
(Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address, Order_Status)
VALUES
(9201,6001,'alice.kim@mail.com',NULL,'active'),
(9202,6002,'john.smith@mail.com',NULL,'active'),
(9203,6003,'sara.lee@mail.com',NULL,'active'),
(9204,6004,'david.ng@mail.com',NULL,'active'),
(9205,6005,NULL,'guest01@mail.com','active'),
(9206,6006,'nina.patel@mail.com',NULL,'active'),
(9207,6007,'mark.brown@mail.com',NULL,'active'),
(9208,6008,'laura.diaz@mail.com',NULL,'active'),
(9209,6009,NULL,'guest02@mail.com','active'),
(9210,6010,'robert.jones@mail.com',NULL,'active');

INSERT INTO Has_an_order (Email_Address, Unique_Order_ID, Quantity_of_tickets) VALUES
('alice.kim@mail.com', 9201, 30),
('john.smith@mail.com',9202, 30),
('sara.lee@mail.com',  9203, 30),
('david.ng@mail.com',  9204, 30),
('guest01@mail.com',   9205, 30),
('nina.patel@mail.com', 9206, 50),
('mark.brown@mail.com', 9207, 50),
('laura.diaz@mail.com', 9208, 50),
('guest02@mail.com',    9209, 50),
('robert.jones@mail.com',9210,50);

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9201, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 108
ORDER BY s.Row_Num, s.Column_Number
LIMIT 30;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9202, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 101
ORDER BY s.Row_Num, s.Column_Number
LIMIT 30;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9203, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 109
ORDER BY s.Row_Num, s.Column_Number
LIMIT 30;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9204, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 106
ORDER BY s.Row_Num, s.Column_Number
LIMIT 30;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9205, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 108
ORDER BY s.Row_Num DESC, s.Column_Number DESC
LIMIT 30;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9206, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 109
ORDER BY s.Row_Num, s.Column_Number
LIMIT 50;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9207, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 106
ORDER BY s.Row_Num, s.Column_Number
LIMIT 50;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9208, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 101
ORDER BY s.Row_Num, s.Column_Number
LIMIT 50;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9209, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 108
ORDER BY s.Row_Num, s.Column_Number
LIMIT 50;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9210, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 109
ORDER BY s.Row_Num DESC, s.Column_Number DESC
LIMIT 50;

-- =========================================================
-- EXTRA: Last 6 months + crew + orders (your block)
-- =========================================================

INSERT INTO Flight
(Flight_ID, Plane_ID, Origin_Airport, Destination_Airport, Departure_Time, Departure_Date, Economy_Price, Business_Price, Flight_Status)
VALUES
(6101,102,1,3,'09:10:00','2025-08-05',330.00,1050.00,'done'),
(6102,104,3,4,'13:40:00','2025-08-18',125.00,440.00,'cancelled'),
(6103,108,1,4,'18:25:00','2025-08-25',265.00,875.00,'done'),
(6111,109,2,3,'08:00:00','2025-09-03',425.00,1410.00,'done'),
(6112,105,9,18,'20:10:00','2025-09-14',515.00,1630.00,'cancelled'),
(6113,101,3,5,'10:30:00','2025-09-22',145.00,480.00,'done'),
(6121,106,15,1,'07:50:00','2025-10-06',165.00,545.00,'done'),
(6122,110,19,20,'21:05:00','2025-10-16',310.00,1010.00,'cancelled'),
(6123,108,18,19,'12:15:00','2025-10-28',245.00,835.00,'done'),
(6131,104,1,9,'14:20:00','2025-11-04',230.00,840.00,'done'),
(6132,102,1,3,'19:40:00','2025-11-12',335.00,1040.00,'cancelled'),
(6133,109,3,4,'08:35:00','2025-11-23',130.00,450.00,'done'),
(6141,105,1,4,'09:00:00','2025-12-02',275.00,910.00,'cancelled'),
(6142,106,9,18,'16:10:00','2025-12-11',505.00,1600.00,'done'),
(6143,101,1,9,'20:30:00','2025-12-19',215.00,790.00,'done'),
(6151,110,2,3,'11:45:00','2026-01-06',415.00,1360.00,'cancelled'),
(6152,109,1,4,'08:10:00','2026-01-15',305.00,1005.00,'done'),
(6153,108,3,4,'18:55:00','2026-01-17',125.00,430.00,'done');

INSERT INTO Pilots_Scheduled_to_Flights (Worker_ID, Flight_ID) VALUES
(3001,6101),(3002,6101),
(3003,6102),(3004,6102),
(3005,6103),(3006,6103),
(3001,6111),(3003,6111),
(3002,6112),(3004,6112),
(3005,6113),(3006,6113),
(3001,6121),(3004,6121),
(3002,6122),(3005,6122),
(3003,6123),(3006,6123),
(3001,6131),(3002,6131),
(3003,6132),(3004,6132),
(3005,6133),(3006,6133),
(3002,6141),(3003,6141),
(3004,6142),(3005,6142),
(3001,6143),(3006,6143),
(3002,6151),(3006,6151),
(3003,6152),(3005,6152),
(3001,6153),(3004,6153);

INSERT INTO Flight_Attendants_Assigned_To_Flights (Worker_ID, Flight_ID) VALUES
(4001,6101),(4002,6101),(4003,6101),
(4004,6102),(4005,6102),(4006,6102),
(4007,6103),(4008,6103),(4009,6103),
(4001,6111),(4002,6111),(4010,6111),
(4003,6112),(4004,6112),(4005,6112),
(4006,6113),(4007,6113),(4008,6113),
(4009,6121),(4010,6121),(4001,6121),
(4002,6122),(4003,6122),(4004,6122),
(4005,6123),(4006,6123),(4007,6123),
(4008,6131),(4009,6131),(4010,6131),
(4001,6132),(4002,6132),(4003,6132),
(4004,6133),(4005,6133),(4006,6133),
(4007,6141),(4008,6141),(4009,6141),
(4010,6142),(4001,6142),(4002,6142),
(4003,6143),(4004,6143),(4005,6143),
(4006,6151),(4007,6151),(4008,6151),
(4009,6152),(4010,6152),(4001,6152),
(4002,6153),(4003,6153),(4004,6153);

INSERT INTO Orders
(Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address, Date_Of_Order, Order_Status)
VALUES
(9301,6101,'alice.kim@mail.com',NULL,'2025-08-01 10:00:00','done'),
(9302,6103,NULL,'guest04@mail.com','2025-08-20 12:30:00','active'),
(9311,6111,'john.smith@mail.com',NULL,'2025-09-01 09:15:00','done'),
(9312,6113,'laura.diaz@mail.com',NULL,'2025-09-18 18:10:00','customercancellation'),
(9321,6121,'mark.brown@mail.com',NULL,'2025-10-02 11:20:00','done'),
(9322,6123,NULL,'guest02@mail.com','2025-10-22 20:05:00','active'),
(9331,6131,'nina.patel@mail.com',NULL,'2025-11-01 08:00:00','done'),
(9332,6133,'sara.lee@mail.com',NULL,'2025-11-20 14:45:00','systemcancellation'),
(9341,6142,'david.ng@mail.com',NULL,'2025-12-06 16:00:00','done'),
(9342,6143,NULL,'guest01@mail.com','2025-12-15 09:30:00','active'),
(9351,6152,'robert.jones@mail.com',NULL,'2026-01-10 13:10:00','done'),
(9352,6153,NULL,'guest03@mail.com','2026-01-14 17:40:00','customercancellation');

INSERT INTO Has_an_order (Email_Address, Unique_Order_ID, Quantity_of_tickets) VALUES
('alice.kim@mail.com',9301,18),
('guest04@mail.com',9302,22),
('john.smith@mail.com',9311,40),
('laura.diaz@mail.com',9312,10),
('mark.brown@mail.com',9321,28),
('guest02@mail.com',9322,35),
('nina.patel@mail.com',9331,45),
('sara.lee@mail.com',9332,12),
('david.ng@mail.com',9341,30),
('guest01@mail.com',9342,26),
('robert.jones@mail.com',9351,38),
('guest03@mail.com',9352,14);

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9301, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 102
ORDER BY s.Row_Num, s.Column_Number
LIMIT 18;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9302, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 108
ORDER BY s.Row_Num, s.Column_Number
LIMIT 22;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9311, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 109
ORDER BY s.Row_Num, s.Column_Number
LIMIT 40;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9312, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 101
ORDER BY s.Row_Num, s.Column_Number
LIMIT 10;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9321, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 106
ORDER BY s.Row_Num, s.Column_Number
LIMIT 28;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9322, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 108
ORDER BY s.Row_Num DESC, s.Column_Number DESC
LIMIT 35;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9331, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 104
ORDER BY s.Row_Num, s.Column_Number
LIMIT 45;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9332, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 109
ORDER BY s.Row_Num, s.Column_Number
LIMIT 12;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9341, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 106
ORDER BY s.Row_Num DESC, s.Column_Number DESC
LIMIT 30;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9342, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 101
ORDER BY s.Row_Num, s.Column_Number
LIMIT 26;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9351, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 109
ORDER BY s.Row_Num, s.Column_Number
LIMIT 38;

INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
SELECT s.Plane_ID, 9352, s.Column_Number, s.Row_Num, 1
FROM Seats s
WHERE s.Plane_ID = 108
ORDER BY s.Row_Num, s.Column_Number
LIMIT 14;

-- Recalculate Final_Total after extra orders
DROP TABLE IF EXISTS tmp_order_totals;
CREATE TEMP TABLE tmp_order_totals AS
SELECT
    o.Unique_Order_ID,
    ROUND(SUM(
        CASE
            WHEN s.Class = 'Business' THEN f.Business_Price
            ELSE f.Economy_Price
        END
    ), 2) AS seats_total
FROM Orders o
JOIN Flight f ON f.Flight_ID = o.Flight_ID
JOIN Selected_Seats ss ON ss.Unique_Order_ID = o.Unique_Order_ID AND ss.Is_Occupied = 1
JOIN Seats s
  ON s.Plane_ID = ss.Plane_ID
 AND s.Row_Num = ss.Row_Num
 AND s.Column_Number = ss.Column_Number
GROUP BY o.Unique_Order_ID;

UPDATE Orders
SET Final_Total =
    CASE
        WHEN Order_Status = 'systemcancellation' THEN 0.00
        WHEN Order_Status = 'customercancellation' THEN ROUND(COALESCE((SELECT seats_total FROM tmp_order_totals t WHERE t.Unique_Order_ID = Orders.Unique_Order_ID), 0.00) * 0.05, 2)
        ELSE COALESCE((SELECT seats_total FROM tmp_order_totals t WHERE t.Unique_Order_ID = Orders.Unique_Order_ID), 0.00)
    END;



-- שאילתה 1
SELECT
    ROUND(AVG(per_flight.occupied_seats / per_flight.total_seats) * 100, 2) AS avg_occupancy_percent
FROM (
    SELECT
        f.Flight_ID,
        COUNT(*) AS occupied_seats,
        (SELECT COUNT(*)
            FROM Seats s
            WHERE s.Plane_ID = f.Plane_ID
        ) AS total_seats
    FROM Flight f
    JOIN Orders o
        ON o.Flight_ID = f.Flight_ID
    JOIN Selected_Seats ss
        ON ss.Unique_Order_ID = o.Unique_Order_ID
       AND ss.Is_Occupied = TRUE
    WHERE f.Flight_Status = 'done'
    GROUP BY f.Flight_ID, f.Plane_ID
) AS per_flight;


-- שאילתה 2
SELECT
    CASE pl.Plane_Size
        WHEN 'LARGE' THEN 'LARGE'
        WHEN 'SMALL' THEN 'SMALL'
        ELSE pl.Plane_Size
    END AS Plane_Size,

    pl.Manufacturer,
    s.Class,

    SUM(
        CASE
            WHEN o.Order_Status IN ('active','done') THEN
                CASE
                    WHEN s.Class = 'Economy'  THEN f.Economy_Price
                    WHEN s.Class = 'Business' THEN f.Business_Price
                END
            WHEN o.Order_Status = 'customercancellation' THEN
                0.05 * CASE
                    WHEN s.Class = 'Economy'  THEN f.Economy_Price
                    WHEN s.Class = 'Business' THEN f.Business_Price
                END
            WHEN o.Order_Status = 'systemcancellation' THEN
                0
            ELSE 0
        END
    ) AS Revenue
FROM Orders o
JOIN Flight f
  ON f.Flight_ID = o.Flight_ID
JOIN Planes pl
  ON pl.Plane_ID = f.Plane_ID
JOIN Selected_Seats ss
  ON ss.Unique_Order_ID = o.Unique_Order_ID
JOIN Seats s
  ON s.Plane_ID = ss.Plane_ID
 AND s.Row_Num = ss.Row_Num
 AND s.Column_Number = ss.Column_Number
GROUP BY
    pl.Plane_Size,
    pl.Manufacturer,
    s.Class;

-- שאילתה 3
SELECT
    w.Worker_ID,
    w.Employee_Type,
    ROUND(SUM(
        CASE
            WHEN r.Duration <= '06:00:00'
            THEN TIME_TO_SEC(r.Duration)
            ELSE 0
        END
    ) / 3600, 2) AS Short_Flight_Hours,
    ROUND(SUM(
        CASE
            WHEN r.Duration > '06:00:00'
            THEN TIME_TO_SEC(r.Duration)
            ELSE 0
        END
    ) / 3600, 2) AS Long_Flight_Hours
FROM (
    -- כל הטייסים
    SELECT Worker_ID, 'Pilot' AS Employee_Type
    FROM Pilots

    UNION ALL

    -- כל הדיילים
    SELECT Worker_ID, 'Flight_Attendant' AS Employee_Type
    FROM Flight_Attendants
) AS w

-- שיבוץ לטיסות (LEFT JOIN כדי שעובד בלי שיבוצים עדיין יופיע)
LEFT JOIN Pilots_Scheduled_to_Flights psf
  ON w.Employee_Type = 'Pilot'
 AND psf.Worker_ID = w.Worker_ID

LEFT JOIN Flight_Attendants_Assigned_To_Flights fa
  ON w.Employee_Type = 'Flight_Attendant'
 AND fa.Worker_ID = w.Worker_ID

-- הטיסה עצמה (רק DONE, ועדיין LEFT JOIN כדי לא להפיל עובדים בלי טיסות DONE)
LEFT JOIN Flight f
  ON f.Flight_ID = COALESCE(psf.Flight_ID, fa.Flight_ID)
 AND f.Flight_Status = 'done'

-- משך טיסה לפי המסלול
LEFT JOIN Routes r
  ON r.Origin_Airport = f.Origin_Airport
 AND r.Destination_Airport = f.Destination_Airport

GROUP BY
    w.Worker_ID,
    w.Employee_Type
ORDER BY
    w.Worker_ID,
    w.Employee_Type;

    -- שאילתה 4
SELECT
    DATE_FORMAT(Date_Of_Order, '%m-%Y') AS month_year,
    ROUND(
        100.0 * SUM(CASE WHEN Order_Status = 'customercancellation' THEN 1 ELSE 0 END)
        / COUNT(*),
        2
    ) AS customer_cancellation_rate_percent
FROM Orders
GROUP BY DATE_FORMAT(Date_Of_Order, '%m-%Y')
ORDER BY MIN(Date_Of_Order);

-- שאילתה 5
SELECT
    p.Plane_ID,
    m.month_year,
    m.flights_performed,
    m.flights_cancelled,
    ROUND(100.0 * m.active_days_done / 30, 2) AS utilization_percent,

    (
        SELECT
            ao.Airport_Name || ' -> ' || ad.Airport_Name
        FROM Flight f2
        JOIN Airports ao ON ao.Airport_ID = f2.Origin_Airport
        JOIN Airports ad ON ad.Airport_ID = f2.Destination_Airport
        WHERE f2.Plane_ID = p.Plane_ID
          AND strftime('%Y-%m', f2.Departure_Date) = m.month_year
          AND f2.Flight_Status = 'done'
        GROUP BY
            f2.Origin_Airport,
            f2.Destination_Airport,
            ao.Airport_Name,
            ad.Airport_Name
        ORDER BY
            COUNT(*) DESC,
            f2.Origin_Airport,
            f2.Destination_Airport
        LIMIT 1)
     AS dominant_origin_destination

FROM Planes p
JOIN (
    SELECT
        Plane_ID,
        strftime('%Y-%m', Departure_Date) AS month_year,

        SUM(CASE
            WHEN Flight_Status = 'done' THEN 1
            ELSE 0
        END) AS flights_performed,

        SUM(CASE
            WHEN Flight_Status = 'cancelled' THEN 1
            ELSE 0
        END) AS flights_cancelled,

        COUNT(DISTINCT CASE
            WHEN Flight_Status = 'done' THEN Departure_Date
            ELSE NULL
        END) AS active_days_done

    FROM Flight
    GROUP BY
        Plane_ID,
        strftime('%Y-%m', Departure_Date))
 AS m
ON m.Plane_ID = p.Plane_ID

ORDER BY
    p.Plane_ID,
    m.month_year;