import { useState } from "react";
import { Award, Plus, Users, User, Calendar, Timer } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Checkbox } from "../components/ui/checkbox";
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

const recentCommendations = [
  {
    id: 1,
    commendationId: "COM-2024-0315-001",
    title: "Project Excellence Award",
    description: "Successfully led Q1 migration project ahead of schedule",
    category: "Category 3",
    monthsReduced: 6,
    employees: ["John Smith (EMP-1001)", "Sarah Johnson (EMP-1002)", "Michael Brown (EMP-1003)"],
    issuedBy: "Admin User",
    date: "2024-03-15",
    type: "Team",
  },
  {
    id: 2,
    commendationId: "COM-2024-0310-001",
    title: "Innovation Award",
    description: "Developed automated testing framework that reduced bug count by 40%",
    category: "Category 2",
    monthsReduced: 3,
    employees: ["Emily Davis (EMP-1004)"],
    issuedBy: "HR Officer",
    date: "2024-03-10",
    type: "Individual",
  },
  {
    id: 3,
    commendationId: "COM-2024-0305-001",
    title: "Customer Service Excellence",
    description: "Received outstanding feedback from 5+ clients this quarter",
    category: "Category 1",
    monthsReduced: 1,
    employees: ["Robert Wilson (EMP-1005)", "Lisa Anderson (EMP-1006)"],
    issuedBy: "Admin User",
    date: "2024-03-05",
    type: "Team",
  },
];

const availableEmployees = [
  { id: "EMP-1001", name: "John Smith", department: "IT", position: "Senior Developer" },
  { id: "EMP-1002", name: "Sarah Johnson", department: "HR", position: "HR Manager" },
  { id: "EMP-1003", name: "Michael Brown", department: "Finance", position: "Financial Analyst" },
  { id: "EMP-1004", name: "Emily Davis", department: "Marketing", position: "Marketing Lead" },
  { id: "EMP-1005", name: "Robert Wilson", department: "Operations", position: "Operations Manager" },
];

export function Commendation() {
  const [mode, setMode] = useState<"single" | "bulk">("single");
  const [selectedEmployees, setSelectedEmployees] = useState<string[]>([]);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    category: "",
    singleEmployee: "",
  });

  const handleEmployeeToggle = (employeeId: string) => {
    setSelectedEmployees((prev) =>
      prev.includes(employeeId)
        ? prev.filter((id) => id !== employeeId)
        : [...prev, employeeId]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In real app, would save to database
    alert(`Commendation issued to ${mode === "single" ? "1 employee" : `${selectedEmployees.length} employees`}`);
    setFormData({ title: "", description: "", singleEmployee: "" });
    setSelectedEmployees([]);
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Commendation Management</h1>
        <p className="text-gray-600">Issue and track employee commendations and awards</p>
      </div>

      <Tabs defaultValue="issue" className="space-y-6">
        <TabsList>
          <TabsTrigger value="issue">Issue Commendation</TabsTrigger>
          <TabsTrigger value="history">Commendation History</TabsTrigger>
        </TabsList>

        {/* Issue Commendation */}
        <TabsContent value="issue">
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Form */}
              <div className="lg:col-span-2 space-y-6">
                {/* Mode Selection */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Commendation Type</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      type="button"
                      onClick={() => setMode("single")}
                      className={`p-6 rounded-lg border-2 transition-all ${
                        mode === "single"
                          ? "border-blue-600 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <User className="w-8 h-8 text-blue-600 mx-auto mb-3" />
                      <h4 className="font-semibold text-gray-900 mb-1">Single Employee</h4>
                      <p className="text-sm text-gray-600">Issue to one employee</p>
                    </button>
                    <button
                      type="button"
                      onClick={() => setMode("bulk")}
                      className={`p-6 rounded-lg border-2 transition-all ${
                        mode === "bulk"
                          ? "border-blue-600 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <Users className="w-8 h-8 text-blue-600 mx-auto mb-3" />
                      <h4 className="font-semibold text-gray-900 mb-1">Team Award</h4>
                      <p className="text-sm text-gray-600">Issue to multiple employees</p>
                    </button>
                  </div>
                </Card>

                {/* Commendation Details */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Commendation Details</h3>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="title">Award Title *</Label>
                      <Input
                        id="title"
                        required
                        placeholder="e.g., Project Excellence Award"
                        value={formData.title}
                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label htmlFor="category">Commendation Category *</Label>
                      <Select value={formData.category} onValueChange={(val) => setFormData({ ...formData, category: val })}>
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="Select category tier" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="category1">Category 1 (−1 month from promotion track)</SelectItem>
                          <SelectItem value="category2">Category 2 (−3 months from promotion track)</SelectItem>
                          <SelectItem value="category3">Category 3 (−6 months from promotion track)</SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-gray-500 mt-1">
                        Higher categories accelerate the employee's promotion race more
                      </p>
                    </div>
                    <div>
                      <Label htmlFor="description">Description *</Label>
                      <Textarea
                        id="description"
                        required
                        placeholder="Describe the achievement or reason for this commendation..."
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        className="mt-1"
                        rows={4}
                      />
                    </div>
                  </div>
                </Card>

                {/* Employee Selection */}
                {mode === "bulk" ? (
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Select Employees</h3>
                      <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                        {selectedEmployees.length} selected
                      </Badge>
                    </div>
                    <div className="space-y-3">
                      {availableEmployees.map((emp) => (
                        <div
                          key={emp.id}
                          className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          <Checkbox
                            id={emp.id}
                            checked={selectedEmployees.includes(emp.id)}
                            onCheckedChange={() => handleEmployeeToggle(emp.id)}
                          />
                          <label htmlFor={emp.id} className="flex-1 cursor-pointer">
                            <p className="font-medium text-gray-900">{emp.name}</p>
                            <p className="text-sm text-gray-600">
                              {emp.position} - {emp.department}
                            </p>
                          </label>
                        </div>
                      ))}
                    </div>
                  </Card>
                ) : (
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Employee</h3>
                    <div className="space-y-3">
                      {availableEmployees.map((emp) => (
                        <label
                          key={emp.id}
                          className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer border-2 transition-all ${
                            formData.singleEmployee === emp.id
                              ? "border-blue-600 bg-blue-50"
                              : "border-gray-200 hover:border-gray-300"
                          }`}
                        >
                          <input
                            type="radio"
                            name="employee"
                            value={emp.id}
                            checked={formData.singleEmployee === emp.id}
                            onChange={(e) => setFormData({ ...formData, singleEmployee: e.target.value })}
                            className="w-4 h-4"
                          />
                          <div>
                            <p className="font-medium text-gray-900">{emp.name}</p>
                            <p className="text-sm text-gray-600">
                              {emp.position} - {emp.department}
                            </p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </Card>
                )}
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                {/* Commendation Impact Info */}
                <Card className="p-6 bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200">
                  <div className="flex items-start gap-3 mb-4">
                    <Timer className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-blue-900 mb-2">Promotion Track Impact</h4>
                      <p className="text-xs text-blue-700 mb-3">
                        Commendations reduce months on the promotion race track
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="p-3 bg-white rounded border border-green-200">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-green-900">Category 1</span>
                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100">−1 month</Badge>
                      </div>
                      <p className="text-xs text-green-700">Good performance recognition</p>
                    </div>

                    <div className="p-3 bg-white rounded border border-blue-200">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-blue-900">Category 2</span>
                        <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">−3 months</Badge>
                      </div>
                      <p className="text-xs text-blue-700">Excellent achievement</p>
                    </div>

                    <div className="p-3 bg-white rounded border border-purple-200">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-purple-900">Category 3</span>
                        <Badge className="bg-purple-100 text-purple-700 hover:bg-purple-100">−6 months</Badge>
                      </div>
                      <p className="text-xs text-purple-700">Outstanding/exceptional work</p>
                    </div>
                  </div>
                </Card>

                {/* Actions */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions</h3>
                  <div className="space-y-3">
                    <Button type="submit" className="w-full gap-2" size="lg">
                      <Award className="w-4 h-4" />
                      Issue Commendation
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full"
                      onClick={() => {
                        setFormData({ title: "", description: "", category: "", singleEmployee: "" });
                        setSelectedEmployees([]);
                      }}
                    >
                      Clear Form
                    </Button>
                  </div>
                </Card>

                {/* Important Rules */}
                <Card className="p-6 bg-yellow-50 border-yellow-200">
                  <div className="flex items-start gap-3">
                    <Award className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-yellow-900 mb-2">Important Rules</h4>
                      <div className="space-y-2 text-sm text-yellow-800">
                        <p>• <strong>Maximum 3 commendations</strong> per employee per role/position</p>
                        <p>• Each commendation gets a unique auto-generated ID</p>
                        <p>• Visible in employee profile & audit log</p>
                        <p>• Can be used for performance reviews</p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </form>
        </TabsContent>

        {/* Commendation History */}
        <TabsContent value="history">
          <Card>
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Recent Commendations</h3>
            </div>
            <div className="p-6">
              <div className="space-y-6">
                {recentCommendations.map((comm) => (
                  <div key={comm.id} className="p-6 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-start gap-4 flex-1">
                        <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Award className="w-6 h-6 text-yellow-600" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-semibold text-gray-900">{comm.title}</h4>
                            <Badge variant="outline" className="text-xs">
                              {comm.commendationId}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600 mb-3">{comm.description}</p>
                          <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              <span>{comm.date}</span>
                            </div>
                            <div>
                              <span>Issued by {comm.issuedBy}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge className={
                              comm.type === "Team"
                                ? "bg-blue-100 text-blue-700 hover:bg-blue-100"
                                : "bg-green-100 text-green-700 hover:bg-green-100"
                            }>
                              {comm.type}
                            </Badge>
                            <Badge className="bg-purple-100 text-purple-700 hover:bg-purple-100">
                              {comm.category}
                            </Badge>
                            <div className="flex items-center gap-1 text-sm font-medium text-green-700">
                              <Timer className="w-4 h-4" />
                              <span>−{comm.monthsReduced} months</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="pl-16">
                      <div className="flex items-center gap-2 mb-2">
                        <Users className="w-4 h-4 text-gray-400" />
                        <span className="text-sm font-medium text-gray-700">Recipients:</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {comm.employees.map((emp, idx) => (
                          <Badge key={idx} variant="outline">
                            {emp}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
