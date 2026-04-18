import { useState } from "react";
import { Link } from "react-router";
import { Search, Filter, Download, UserPlus, Eye, Edit, Trash2 } from "lucide-react";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

const employees = [
  {
    id: "EMP-1001",
    name: "John Smith",
    email: "john.smith@company.com",
    department: "IT",
    position: "Senior Developer",
    level: "L6",
    status: "Active",
    joinDate: "2020-03-15",
  },
  {
    id: "EMP-1002",
    name: "Sarah Johnson",
    email: "sarah.j@company.com",
    department: "HR",
    position: "HR Manager",
    level: "L5",
    status: "Active",
    joinDate: "2018-07-22",
  },
  {
    id: "EMP-1003",
    name: "Michael Brown",
    email: "m.brown@company.com",
    department: "Finance",
    position: "Financial Analyst",
    level: "L7",
    status: "Active",
    joinDate: "2021-11-10",
  },
  {
    id: "EMP-1004",
    name: "Emily Davis",
    email: "emily.d@company.com",
    department: "Marketing",
    position: "Marketing Lead",
    level: "L6",
    status: "Active",
    joinDate: "2019-05-08",
  },
  {
    id: "EMP-1005",
    name: "Robert Wilson",
    email: "r.wilson@company.com",
    department: "Operations",
    position: "Operations Manager",
    level: "L5",
    status: "On Leave",
    joinDate: "2017-02-14",
  },
  {
    id: "EMP-1006",
    name: "Lisa Anderson",
    email: "lisa.a@company.com",
    department: "IT",
    position: "Junior Developer",
    level: "L7",
    status: "Active",
    joinDate: "2022-09-01",
  },
  {
    id: "EMP-1007",
    name: "David Martinez",
    email: "d.martinez@company.com",
    department: "Sales",
    position: "Sales Director",
    level: "L4",
    status: "Active",
    joinDate: "2016-12-05",
  },
  {
    id: "EMP-1008",
    name: "Jennifer Taylor",
    email: "j.taylor@company.com",
    department: "Finance",
    position: "Accountant",
    level: "L7",
    status: "Active",
    joinDate: "2023-01-20",
  },
];

export function EmployeeList() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterDepartment, setFilterDepartment] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

  const filteredEmployees = employees.filter((emp) => {
    const matchesSearch = 
      emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.email.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesDepartment = filterDepartment === "all" || emp.department === filterDepartment;
    const matchesStatus = filterStatus === "all" || emp.status === filterStatus;

    return matchesSearch && matchesDepartment && matchesStatus;
  });

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Employee Management</h1>
        <p className="text-gray-600">Manage and view all employee records</p>
      </div>

      {/* Actions Bar */}
      <Card className="p-4 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <Input
              placeholder="Search by name, ID, or email..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Filters */}
          <div className="flex gap-3">
            <Select value={filterDepartment} onValueChange={setFilterDepartment}>
              <SelectTrigger className="w-[180px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                <SelectItem value="IT">IT</SelectItem>
                <SelectItem value="HR">HR</SelectItem>
                <SelectItem value="Finance">Finance</SelectItem>
                <SelectItem value="Marketing">Marketing</SelectItem>
                <SelectItem value="Operations">Operations</SelectItem>
                <SelectItem value="Sales">Sales</SelectItem>
              </SelectContent>
            </Select>

            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="Active">Active</SelectItem>
                <SelectItem value="On Leave">On Leave</SelectItem>
                <SelectItem value="Inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>

            <Button variant="outline" className="gap-2">
              <Download className="w-4 h-4" />
              Export
            </Button>

            <Link to="/employees/new">
              <Button className="gap-2">
                <UserPlus className="w-4 h-4" />
                Add Employee
              </Button>
            </Link>
          </div>
        </div>
      </Card>

      {/* Results Info */}
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Showing <span className="font-medium">{filteredEmployees.length}</span> of{" "}
          <span className="font-medium">{employees.length}</span> employees
        </p>
      </div>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Employee ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Department</TableHead>
              <TableHead>Position</TableHead>
              <TableHead>Level</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEmployees.map((employee) => (
              <TableRow key={employee.id}>
                <TableCell className="font-medium">{employee.id}</TableCell>
                <TableCell>{employee.name}</TableCell>
                <TableCell className="text-gray-600">{employee.email}</TableCell>
                <TableCell>
                  <Badge variant="outline">{employee.department}</Badge>
                </TableCell>
                <TableCell>{employee.position}</TableCell>
                <TableCell>
                  <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                    {employee.level}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge
                    className={
                      employee.status === "Active"
                        ? "bg-green-100 text-green-700 hover:bg-green-100"
                        : "bg-yellow-100 text-yellow-700 hover:bg-yellow-100"
                    }
                  >
                    {employee.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-2">
                    <Link to={`/employees/${employee.id}`}>
                      <Button variant="ghost" size="sm">
                        <Eye className="w-4 h-4" />
                      </Button>
                    </Link>
                    <Button variant="ghost" size="sm">
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
