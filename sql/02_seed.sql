-- Sample data. Only inserts into empty tables, so it is safe to re-run.
IF NOT EXISTS (SELECT 1 FROM dbo.Department)
INSERT INTO dbo.Department (DepartmentID, DepartmentName, Location) VALUES
    (1, 'Engineering', 'Pune'),
    (2, 'Sales',       'Mumbai'),
    (3, 'HR',          'Pune'),
    (4, 'Finance',     NULL);
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Employee)
INSERT INTO dbo.Employee (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate) VALUES
    ('Aarav',  'Sharma',   1, 125000.00,  5000.00, '2018-03-12'),  -- highest salary, NOT highest total comp
    ('Diya',   'Patel',    1, 110000.00,   NULL,   '2019-07-01'),
    ('Rohan',  'Mehta',    1,  95000.00,  8000.00, '2021-01-15'),
    ('Sneha',  'Kulkarni', 2,  60000.00, 40000.00, '2020-05-20'),
    ('Vikram', 'Singh',    2,  70000.00, 35000.00, '2017-11-30'),  -- Sales: bonuses 75k > avg salary 70k
    ('Anjali', 'Nair',     2,  80000.00,   NULL,   '2022-02-10'),
    ('Karan',  'Verma',    3,  55000.00,   NULL,   '2023-06-05'),
    ('Pooja',  'Desai',    3,  58000.00,  2900.00, '2016-09-18'),
    ('Neha',   'Joshi',    4, 118000.00, 25000.00, '2015-04-22');  -- highest total compensation (143,000)
GO
