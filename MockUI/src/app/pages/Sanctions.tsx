import { useState } from "react";
import { AlertTriangle, Plus, Calendar, User, Timer } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
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

const activeSanctions = [
  {
    id: 1,
    sanctionId: "SAN-2024-0310-001",
    employeeId: "EMP-1003",
    employeeName: "Michael Brown",
    type: "Written Warning",
    reason: "Repeated late submissions of monthly reports",
    issueDate: "2024-03-10",
    durationMonths: 3,
    status: "Active",
    issuedBy: "HR Officer",
  },
  {
    id: 2,
    sanctionId: "SAN-2024-0315-001",
    employeeId: "EMP-1007",
    employeeName: "David Martinez",
    type: "Verbal Warning",
    reason: "Violation of company attendance policy",
    issueDate: "2024-03-15",
    durationMonths: 1,
    status: "Active",
    issuedBy: "Admin User",
  },
];

const sanctionHistory = [
  {
    id: 3,
    sanctionId: "SAN-2023-1210-001",
    employeeId: "EMP-1001",
    employeeName: "John Smith",
    type: "Verbal Warning",
    reason: "Late submission of quarterly report",
    issueDate: "2023-12-10",
    durationMonths: 2,
    status: "Resolved",
    issuedBy: "HR Officer",
  },
  {
    id: 4,
    sanctionId: "SAN-2023-1120-001",
    employeeId: "EMP-1005",
    employeeName: "Robert Wilson",
    type: "Written Warning",
    reason: "Unprofessional conduct in team meeting",
    issueDate: "2023-11-20",
    durationMonths: 4,
    status: "Resolved",
    issuedBy: "Admin User",
  },
];

const availableEmployees = [
  { id: "EMP-1001", name: "John Smith", department: "IT", position: "Senior Developer" },
  { id: "EMP-1002", name: "Sarah Johnson", department: "HR", position: "HR Manager" },
  { id: "EMP-1003", name: "Michael Brown", department: "Finance", position: "Financial Analyst" },
  { id: "EMP-1004", name: "Emily Davis", department: "Marketing", position: "Marketing Lead" },
  { id: "EMP-1005", name: "Robert Wilson", department: "Operations", position: "Operations Manager" },
];

export function Sanctions() {
  const [formData, setFormData] = useState({
    employee: "",
    type: "",
    reason: "",
    durationMonths: "",
    issueDate: new Date().toISOString().split("T")[0],
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert("Sanction issued successfully");
    setFormData({
      employee: "",
      type: "",
      reason: "",
      durationMonths: "",
      issueDate: new Date().toISOString().split("T")[0],
    });
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Sanctions Management</h1>
        <p className="text-gray-600">Manage employee disciplinary actions and warnings</p>
      </div>

      <Tabs defaultValue="active" className="space-y-6">
        <TabsList>
          <TabsTrigger value="active">Active Sanctions</TabsTrigger>
          <TabsTrigger value="history">Sanction History</TabsTrigger>
          <TabsTrigger value="issue">Issue Sanction</TabsTrigger>
        </TabsList>

        {/* Active Sanctions */}
        <TabsContent value="active">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Active Sanctions</p>
                  <p className="text-2xl font-bold text-gray-900">{activeSanctions.length}</p>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-yellow-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Expiring Soon</p>
                  <p className="text-2xl font-bold text-gray-900">1</p>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Resolved This Month</p>
                  <p className="text-2xl font-bold text-gray-900">2</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Table */}
          <Card>
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Current Active Sanctions</h3>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sanction ID</TableHead>
                  <TableHead>Employee</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Issue Date</TableHead>
                  <TableHead>Promotion Delay</TableHead>
                  <TableHead>Issued By</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeSanctions.map((sanction) => (
                  <TableRow key={sanction.id}>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {sanction.sanctionId}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium text-gray-900">{sanction.employeeName}</p>
                        <p className="text-sm text-gray-500">{sanction.employeeId}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-red-100 text-red-700 hover:bg-red-100">
                        {sanction.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs text-sm text-gray-600">{sanction.reason}</TableCell>
                    <TableCell>{sanction.issueDate}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm font-medium text-red-700">
                        <Timer className="w-4 h-4" />
                        <span>+{sanction.durationMonths} {sanction.durationMonths === 1 ? 'month' : 'months'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">{sanction.issuedBy}</TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="outline" size="sm">
                          Mark Resolved
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Sanction History */}
        <TabsContent value="history">
          <Card>
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Resolved Sanctions</h3>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sanction ID</TableHead>
                  <TableHead>Employee</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Issue Date</TableHead>
                  <TableHead>Delay Applied</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Issued By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sanctionHistory.map((sanction) => (
                  <TableRow key={sanction.id}>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {sanction.sanctionId}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium text-gray-900">{sanction.employeeName}</p>
                        <p className="text-sm text-gray-500">{sanction.employeeId}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{sanction.type}</Badge>
                    </TableCell>
                    <TableCell className="max-w-xs text-sm text-gray-600">{sanction.reason}</TableCell>
                    <TableCell>{sanction.issueDate}</TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-600">
                        +{sanction.durationMonths} {sanction.durationMonths === 1 ? 'month' : 'months'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                        {sanction.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">{sanction.issuedBy}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Issue Sanction */}
        <TabsContent value="issue">
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Form */}
              <div className="lg:col-span-2">
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Issue New Sanction</h3>
                  <div className="space-y-6">
                    {/* Employee Selection */}
                    <div>
                      <Label htmlFor="employee">Select Employee *</Label>
                      <Select value={formData.employee} onValueChange={(val) => setFormData({ ...formData, employee: val })}>
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="Choose an employee" />
                        </SelectTrigger>
                        <SelectContent>
                          {availableEmployees.map((emp) => (
                            <SelectItem key={emp.id} value={emp.id}>
                              {emp.name} - {emp.position} ({emp.department})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Sanction Type */}
                    <div>
                      <Label htmlFor="type">Sanction Type *</Label>
                      <Select value={formData.type} onValueChange={(val) => setFormData({ ...formData, type: val })}>
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="Select sanction type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="verbal">Verbal Warning</SelectItem>
                          <SelectItem value="written">Written Warning</SelectItem>
                          <SelectItem value="suspension">Suspension</SelectItem>
                          <SelectItem value="final">Final Warning</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Reason */}
                    <div>
                      <Label htmlFor="reason">Reason/Description *</Label>
                      <Textarea
                        id="reason"
                        required
                        placeholder="Describe the reason for this sanction..."
                        value={formData.reason}
                        onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                        className="mt-1"
                        rows={4}
                      />
                    </div>

                    {/* Duration and Date */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="issueDate">Issue Date *</Label>
                        <Input
                          id="issueDate"
                          type="date"
                          required
                          value={formData.issueDate}
                          onChange={(e) => setFormData({ ...formData, issueDate: e.target.value })}
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label htmlFor="durationMonths">Promotion Delay (months) *</Label>
                        <Select value={formData.durationMonths} onValueChange={(val) => setFormData({ ...formData, durationMonths: val })}>
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select delay in months" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="1">1 month</SelectItem>
                            <SelectItem value="2">2 months</SelectItem>
                            <SelectItem value="3">3 months</SelectItem>
                            <SelectItem value="4">4 months</SelectItem>
                            <SelectItem value="5">5 months</SelectItem>
                            <SelectItem value="6">6 months</SelectItem>
                            <SelectItem value="7">7 months</SelectItem>
                            <SelectItem value="8">8 months</SelectItem>
                            <SelectItem value="9">9 months</SelectItem>
                            <SelectItem value="10">10 months</SelectItem>
                            <SelectItem value="11">11 months</SelectItem>
                            <SelectItem value="12">12 months</SelectItem>
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-gray-500 mt-1">
                          How many months this adds to the promotion race
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                {/* Actions */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions</h3>
                  <div className="space-y-3">
                    <Button type="submit" className="w-full gap-2" size="lg">
                      <AlertTriangle className="w-4 h-4" />
                      Issue Sanction
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full"
                      onClick={() =>
                        setFormData({
                          employee: "",
                          type: "",
                          reason: "",
                          durationMonths: "",
                          issueDate: new Date().toISOString().split("T")[0],
                        })
                      }
                    >
                      Clear Form
                    </Button>
                  </div>
                </Card>

                {/* Promotion Impact */}
                <Card className="p-6 bg-gradient-to-br from-red-50 to-orange-50 border-red-200">
                  <div className="flex items-start gap-3">
                    <Timer className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-red-900 mb-2">Promotion Race Impact</h4>
                      <div className="space-y-2 text-sm text-red-800">
                        <p>• Sanctions <strong>delay the promotion race</strong> by adding months to the timeline</p>
                        <p>• The employee must wait longer before becoming eligible for promotion</p>
                        <p>• Duration range: <strong>1-12 months</strong></p>
                        <p>• Each sanction receives a <strong>unique auto-generated ID</strong></p>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Warning Info */}
                <Card className="p-6 bg-red-50 border-red-200">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-red-900 mb-2">Important Notes</h4>
                      <div className="space-y-2 text-sm text-red-800">
                        <p>• All sanctions are recorded in the audit log</p>
                        <p>• Employee will be notified of the sanction</p>
                        <p>• Sanctions directly impact promotion timeline</p>
                        <p>• Ensure proper documentation is attached</p>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Sanction Guidelines */}
                <Card className="p-6 bg-blue-50 border-blue-200">
                  <div className="flex items-start gap-3">
                    <User className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-blue-900 mb-2">Sanction Guidelines</h4>
                      <div className="space-y-2 text-sm text-blue-800">
                        <div>
                          <p className="font-medium">Verbal Warning:</p>
                          <p>Minor violations (1-2 months delay)</p>
                        </div>
                        <div>
                          <p className="font-medium">Written Warning:</p>
                          <p>Repeated violations (3-6 months delay)</p>
                        </div>
                        <div>
                          <p className="font-medium">Final Warning:</p>
                          <p>Severe misconduct (6-12 months delay)</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </form>
        </TabsContent>
      </Tabs>
    </div>
  );
}
