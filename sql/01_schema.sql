-- Employee Compensation Service: schema (SQL Server / Azure SQL). Safe to re-run.
IF OBJECT_ID('dbo.Department', 'U') IS NULL
CREATE TABLE dbo.Department (
    DepartmentID   INT           NOT NULL CONSTRAINT PK_Department PRIMARY KEY,
    DepartmentName VARCHAR(100)  NOT NULL,
    Location       VARCHAR(100)  NULL
);
GO

IF OBJECT_ID('dbo.Employee', 'U') IS NULL
CREATE TABLE dbo.Employee (
    EmployeeID   INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Employee PRIMARY KEY,
    FirstName    VARCHAR(50)    NOT NULL,
    LastName     VARCHAR(50)    NOT NULL,
    DepartmentID INT            NOT NULL
        CONSTRAINT FK_Employee_Department REFERENCES dbo.Department (DepartmentID),
    Salary       DECIMAL(12,2)  NOT NULL CONSTRAINT CK_Employee_Salary CHECK (Salary >= 0),
    Bonus        DECIMAL(12,2)  NULL     CONSTRAINT CK_Employee_Bonus  CHECK (Bonus IS NULL OR Bonus >= 0), -- NULL = no bonus
    HireDate     DATE           NULL
);
GO

-- Supports the department filter and the department join in reports
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Employee_DepartmentID')
    CREATE INDEX IX_Employee_DepartmentID ON dbo.Employee (DepartmentID);
GO
