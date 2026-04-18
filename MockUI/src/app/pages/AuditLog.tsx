import { useState } from "react";
import { FileText, Search, Filter, Download, User, Calendar } from "lucide-react";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

const auditLogs = [
  {
    id: 1,
    timestamp: "2024-04-06 14:32:15",
    user: "Admin User",
    action: "Employee Added",
    target: "John Smith (EMP-1248)",
    details: "New employee record created with L6 level",
    category: "Employee Management",
  },
  {
    id: 2,
    timestamp: "2024-04-06 13:15:42",
    user: "HR Officer",
    action: "Promotion Approved",
    target: "Sarah Johnson (EMP-1002)",
    details: "Promoted from L7 to L6 - Met eligibility requirements",
    category: "Promotions",
  },
  {
    id: 3,
    timestamp: "2024-04-06 11:20:30",
    user: "Admin User",
    action: "Commendation Issued",
    target: "Team Award - 5 employees",
    details: "Project Excellence Award issued to development team",
    category: "Commendations",
  },
  {
    id: 4,
    timestamp: "2024-04-06 10:45:18",
    user: "HR Officer",
    action: "Sanction Applied",
    target: "Michael Brown (EMP-1003)",
    details: "Written Warning - Late submission of reports",
    category: "Sanctions",
  },
  {
    id: 5,
    timestamp: "2024-04-06 09:30:05",
    user: "Admin User",
    action: "CSV Import",
    target: "Employee Data",
    details: "Successfully imported 45 employee records",
    category: "Data Import",
  },
  {
    id: 6,
    timestamp: "2024-04-05 16:55:22",
    user: "HR Officer",
    action: "Employee Updated",
    target: "Emily Davis (EMP-1004)",
    details: "Department changed from Marketing to Sales",
    category: "Employee Management",
  },
  {
    id: 7,
    timestamp: "2024-04-05 15:10:40",
    user: "Admin User",
    action: "Settings Modified",
    target: "Promotion Rules",
    details: "Updated L6→L5 commendation requirement from 2 to 3",
    category: "Settings",
  },
  {
    id: 8,
    timestamp: "2024-04-05 14:22:33",
    user: "Admin User",
    action: "Organization Unit Added",
    target: "IT Department - Security Unit",
    details: "New unit created under IT Department",
    category: "Hierarchy",
  },
  {
    id: 9,
    timestamp: "2024-04-05 13:05:12",
    user: "HR Officer",
    action: "Sanction Resolved",
    target: "Robert Wilson (EMP-1005)",
    details: "Verbal Warning marked as resolved after 30 days",
    category: "Sanctions",
  },
  {
    id: 10,
    timestamp: "2024-04-05 11:40:55",
    user: "Admin User",
    action: "Employee Deleted",
    target: "Jane Doe (EMP-1099)",
    details: "Employee record removed - Termination processed",
    category: "Employee Management",
  },
];

export function AuditLog() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterUser, setFilterUser] = useState("all");

  const filteredLogs = auditLogs.filter((log) => {
    const matchesSearch =
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.target.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.details.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory = filterCategory === "all" || log.category === filterCategory;
    const matchesUser = filterUser === "all" || log.user === filterUser;

    return matchesSearch && matchesCategory && matchesUser;
  });

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "Employee Management":
        return "bg-blue-100 text-blue-700 hover:bg-blue-100";
      case "Promotions":
        return "bg-green-100 text-green-700 hover:bg-green-100";
      case "Commendations":
        return "bg-yellow-100 text-yellow-700 hover:bg-yellow-100";
      case "Sanctions":
        return "bg-red-100 text-red-700 hover:bg-red-100";
      case "Data Import":
        return "bg-purple-100 text-purple-700 hover:bg-purple-100";
      case "Settings":
        return "bg-gray-100 text-gray-700 hover:bg-gray-100";
      case "Hierarchy":
        return "bg-indigo-100 text-indigo-700 hover:bg-indigo-100";
      default:
        return "bg-gray-100 text-gray-700 hover:bg-gray-100";
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Audit Log</h1>
        <p className="text-gray-600">Complete record of all system activities and changes</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Logs</p>
              <p className="text-2xl font-bold text-gray-900">{auditLogs.length}</p>
            </div>
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <User className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Today's Activities</p>
              <p className="text-2xl font-bold text-gray-900">5</p>
            </div>
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <Calendar className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">This Week</p>
              <p className="text-2xl font-bold text-gray-900">10</p>
            </div>
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Most Active User</p>
              <p className="text-lg font-bold text-gray-900">Admin User</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <Input
              placeholder="Search actions, targets, or details..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Category Filter */}
          <Select value={filterCategory} onValueChange={setFilterCategory}>
            <SelectTrigger className="w-[200px]">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="Employee Management">Employee Management</SelectItem>
              <SelectItem value="Promotions">Promotions</SelectItem>
              <SelectItem value="Commendations">Commendations</SelectItem>
              <SelectItem value="Sanctions">Sanctions</SelectItem>
              <SelectItem value="Data Import">Data Import</SelectItem>
              <SelectItem value="Settings">Settings</SelectItem>
              <SelectItem value="Hierarchy">Hierarchy</SelectItem>
            </SelectContent>
          </Select>

          {/* User Filter */}
          <Select value={filterUser} onValueChange={setFilterUser}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="User" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Users</SelectItem>
              <SelectItem value="Admin User">Admin User</SelectItem>
              <SelectItem value="HR Officer">HR Officer</SelectItem>
            </SelectContent>
          </Select>

          <Button variant="outline" className="gap-2">
            <Download className="w-4 h-4" />
            Export
          </Button>
        </div>
      </Card>

      {/* Results Count */}
      <div className="mb-4">
        <p className="text-sm text-gray-600">
          Showing <span className="font-medium">{filteredLogs.length}</span> of{" "}
          <span className="font-medium">{auditLogs.length}</span> log entries
        </p>
      </div>

      {/* Audit Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Details</TableHead>
              <TableHead>Category</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredLogs.map((log) => (
              <TableRow key={log.id}>
                <TableCell className="font-mono text-sm text-gray-600">
                  {log.timestamp}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-blue-600" />
                    </div>
                    <span className="font-medium text-gray-900">{log.user}</span>
                  </div>
                </TableCell>
                <TableCell className="font-medium text-gray-900">{log.action}</TableCell>
                <TableCell className="text-gray-600">{log.target}</TableCell>
                <TableCell className="text-sm text-gray-600 max-w-md">{log.details}</TableCell>
                <TableCell>
                  <Badge className={getCategoryColor(log.category)}>{log.category}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Info Note */}
      <Card className="mt-6 p-6 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <FileText className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold text-blue-900 mb-2">Audit Log Information</h4>
            <div className="space-y-1 text-sm text-blue-800">
              <p>• All system activities are automatically logged for compliance and security</p>
              <p>• Logs cannot be modified or deleted to ensure data integrity</p>
              <p>• Records include user identity, timestamp, and detailed action information</p>
              <p>• Logs are retained indefinitely for audit purposes</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
