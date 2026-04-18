import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, Save, GraduationCap, Info } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";

export function AddEmployee() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    address: "",
    degree: "",
    department: "",
    position: "",
    reportingTo: "",
    joinDate: "",
    baseSalary: "",
  });

  const [autoLevel, setAutoLevel] = useState("");

  const handleDegreeChange = (degree: string) => {
    setFormData({ ...formData, degree });
    
    // Auto-assign level based on degree
    switch (degree) {
      case "PhD":
        setAutoLevel("L5");
        break;
      case "MSc":
        setAutoLevel("L6");
        break;
      case "BSc":
        setAutoLevel("L7");
        break;
      default:
        setAutoLevel("");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In real app, would save to database
    navigate("/employees");
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <Link to="/employees">
          <Button variant="ghost" className="gap-2 mb-4">
            <ArrowLeft className="w-4 h-4" />
            Back to Employees
          </Button>
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Add New Employee</h1>
        <p className="text-gray-600">Fill in the employee details to add them to the system</p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Personal Information */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Personal Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="firstName">First Name *</Label>
                  <Input
                    id="firstName"
                    required
                    value={formData.firstName}
                    onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="lastName">Last Name *</Label>
                  <Input
                    id="lastName"
                    required
                    value={formData.lastName}
                    onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="phone">Phone Number *</Label>
                  <Input
                    id="phone"
                    required
                    placeholder="+36 20 123 4567"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="address">Address</Label>
                  <Textarea
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className="mt-1"
                    rows={2}
                  />
                </div>
              </div>
            </Card>

            {/* Education & Level */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Education & Level Assignment</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="degree">Highest Degree *</Label>
                  <Select value={formData.degree} onValueChange={handleDegreeChange}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select degree" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PhD">PhD</SelectItem>
                      <SelectItem value="MSc">MSc / Master's</SelectItem>
                      <SelectItem value="BSc">BSc / Bachelor's</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="autoLevel">Auto-Assigned Level</Label>
                  <div className="mt-1 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2">
                    <GraduationCap className="w-5 h-5 text-blue-600" />
                    <span className="font-medium text-blue-900">
                      {autoLevel || "Select degree first"}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    PhD → L5 | MSc → L6 | BSc → L7
                  </p>
                </div>
              </div>
            </Card>

            {/* Employment Details */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Employment Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="department">Department *</Label>
                  <Select value={formData.department} onValueChange={(val) => setFormData({ ...formData, department: val })}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select department" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="IT">IT</SelectItem>
                      <SelectItem value="HR">HR</SelectItem>
                      <SelectItem value="Finance">Finance</SelectItem>
                      <SelectItem value="Marketing">Marketing</SelectItem>
                      <SelectItem value="Operations">Operations</SelectItem>
                      <SelectItem value="Sales">Sales</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="position">Position/Title *</Label>
                  <Input
                    id="position"
                    required
                    placeholder="e.g., Senior Developer"
                    value={formData.position}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="reportingTo">Reporting To</Label>
                  <Select value={formData.reportingTo} onValueChange={(val) => setFormData({ ...formData, reportingTo: val })}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select manager" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EMP-1002">Sarah Johnson - HR Manager</SelectItem>
                      <SelectItem value="EMP-1007">David Martinez - Sales Director</SelectItem>
                      <SelectItem value="None">No Direct Manager</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="joinDate">Join Date *</Label>
                  <Input
                    id="joinDate"
                    type="date"
                    required
                    value={formData.joinDate}
                    onChange={(e) => setFormData({ ...formData, joinDate: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="baseSalary">Base Salary (EUR) *</Label>
                  <Input
                    id="baseSalary"
                    type="number"
                    required
                    placeholder="e.g., 3500"
                    value={formData.baseSalary}
                    onChange={(e) => setFormData({ ...formData, baseSalary: e.target.value })}
                    className="mt-1"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Recommended: €2,000 - €3,000 for {autoLevel}
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Sidebar - Help & Actions */}
          <div className="space-y-6">
            {/* Actions */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions</h3>
              <div className="space-y-3">
                <Button type="submit" className="w-full gap-2">
                  <Save className="w-4 h-4" />
                  Save Employee
                </Button>
                <Link to="/employees" className="block">
                  <Button type="button" variant="outline" className="w-full">
                    Cancel
                  </Button>
                </Link>
              </div>
            </Card>

            {/* Level Assignment Rules */}
            <Card className="p-6 bg-blue-50 border-blue-200">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-blue-900 mb-2">Level Assignment Rules</h4>
                  <div className="space-y-2 text-sm text-blue-800">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                      <span>PhD degree → starts at L5</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                      <span>MSc degree → starts at L6</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                      <span>BSc degree → starts at L7</span>
                    </div>
                  </div>
                </div>
              </div>
            </Card>

            {/* Salary Guidelines */}
            <Card className="p-6 bg-green-50 border-green-200">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-green-900 mb-2">Salary Guidelines</h4>
                  <div className="space-y-2 text-sm text-green-800">
                    <div>
                      <p className="font-medium">L7: €2,000 - €2,800</p>
                    </div>
                    <div>
                      <p className="font-medium">L6: €2,800 - €3,500</p>
                    </div>
                    <div>
                      <p className="font-medium">L5: €3,500 - €4,500</p>
                    </div>
                    <p className="text-xs mt-2">
                      Base salary can be adjusted based on location and market conditions
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </form>
    </div>
  );
}
