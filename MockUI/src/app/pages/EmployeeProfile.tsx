import { useState } from "react";
import { useParams, Link } from "react-router";
import { ArrowLeft, Mail, Phone, MapPin, Calendar, Award, TrendingUp, AlertTriangle, Edit } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";

const employeeData = {
  id: "EMP-1001",
  name: "John Smith",
  email: "john.smith@company.com",
  phone: "+36 20 123 4567",
  position: "Senior Developer",
  department: "IT",
  level: "L6",
  status: "Active",
  joinDate: "2020-03-15",
  degree: "MSc Computer Science",
  baseSalary: "€3,500",
  reportingTo: "Sarah Johnson (EMP-1002)",
  address: "Budapest, Hungary",
  linkedin: "linkedin.com/in/johnsmith",
  
  promotionHistory: [
    { date: "2023-01-15", from: "L7", to: "L6", reason: "Performance + 3 years service" },
    { date: "2020-03-15", from: "-", to: "L7", reason: "Initial hire (MSc degree)" },
  ],
  
  commendations: [
    { date: "2024-02-20", title: "Project Excellence Award", description: "Led successful migration project", issuedBy: "Admin User" },
    { date: "2023-09-10", title: "Team Collaboration", description: "Exceptional teamwork on Q3 deliverables", issuedBy: "HR Officer" },
    { date: "2022-12-05", title: "Innovation Award", description: "Implemented new automation framework", issuedBy: "Admin User" },
  ],
  
  sanctions: [
    { date: "2021-06-15", type: "Verbal Warning", reason: "Late submission of reports", duration: "Resolved", issuedBy: "HR Officer" },
  ],
};

export function EmployeeProfile() {
  const { id } = useParams();
  const [isEditing, setIsEditing] = useState(false);

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
      </div>

      {/* Profile Header */}
      <Card className="p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex gap-6">
            {/* Avatar */}
            <div className="w-24 h-24 bg-blue-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
              {employeeData.name.split(' ').map(n => n[0]).join('')}
            </div>
            
            {/* Info */}
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-900">{employeeData.name}</h1>
                <Badge className={
                  employeeData.status === "Active"
                    ? "bg-green-100 text-green-700 hover:bg-green-100"
                    : "bg-yellow-100 text-yellow-700 hover:bg-yellow-100"
                }>
                  {employeeData.status}
                </Badge>
                <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                  {employeeData.level}
                </Badge>
              </div>
              <p className="text-lg text-gray-600 mb-4">{employeeData.position}</p>
              
              <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                <div className="flex items-center gap-2 text-gray-600">
                  <Mail className="w-4 h-4" />
                  <span className="text-sm">{employeeData.email}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <Phone className="w-4 h-4" />
                  <span className="text-sm">{employeeData.phone}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <MapPin className="w-4 h-4" />
                  <span className="text-sm">{employeeData.address}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <Calendar className="w-4 h-4" />
                  <span className="text-sm">Joined {employeeData.joinDate}</span>
                </div>
              </div>
            </div>
          </div>

          <Button className="gap-2" onClick={() => setIsEditing(!isEditing)}>
            <Edit className="w-4 h-4" />
            {isEditing ? "Save Changes" : "Edit Profile"}
          </Button>
        </div>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="details" className="space-y-6">
        <TabsList>
          <TabsTrigger value="details">Personal Details</TabsTrigger>
          <TabsTrigger value="promotions">Promotion History</TabsTrigger>
          <TabsTrigger value="commendations">Commendations</TabsTrigger>
          <TabsTrigger value="sanctions">Sanctions</TabsTrigger>
        </TabsList>

        {/* Personal Details */}
        <TabsContent value="details">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Employment Information</h3>
              <div className="space-y-4">
                <div>
                  <Label>Employee ID</Label>
                  <Input value={employeeData.id} disabled className="mt-1" />
                </div>
                <div>
                  <Label>Department</Label>
                  <Input value={employeeData.department} disabled={!isEditing} className="mt-1" />
                </div>
                <div>
                  <Label>Position</Label>
                  <Input value={employeeData.position} disabled={!isEditing} className="mt-1" />
                </div>
                <div>
                  <Label>Level</Label>
                  <Input value={employeeData.level} disabled className="mt-1" />
                </div>
                <div>
                  <Label>Reporting To</Label>
                  <Input value={employeeData.reportingTo} disabled={!isEditing} className="mt-1" />
                </div>
                <div>
                  <Label>Join Date</Label>
                  <Input type="date" value={employeeData.joinDate} disabled className="mt-1" />
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Personal Information (Admin Only)</h3>
              <div className="space-y-4">
                <div>
                  <Label>Full Name</Label>
                  <Input value={employeeData.name} disabled={!isEditing} className="mt-1" />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input value={employeeData.email} disabled={!isEditing} className="mt-1" />
                </div>
                <div>
                  <Label>Phone</Label>
                  <Input value={employeeData.phone} disabled={!isEditing} className="mt-1" />
                </div>
                <div>
                  <Label>Address</Label>
                  <Input value={employeeData.address} disabled={!isEditing} className="mt-1" />
                </div>
                <div>
                  <Label>Degree</Label>
                  <Input value={employeeData.degree} disabled className="mt-1" />
                </div>
                <div>
                  <Label>Base Salary</Label>
                  <Input value={employeeData.baseSalary} disabled={!isEditing} className="mt-1" />
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Employee-Editable Fields</h3>
              <div className="space-y-4">
                <div>
                  <Label>LinkedIn Profile</Label>
                  <Input value={employeeData.linkedin} className="mt-1" />
                  <p className="text-xs text-gray-500 mt-1">Employee can update this field</p>
                </div>
                <div>
                  <Label>Status</Label>
                  <Input value={employeeData.status} className="mt-1" />
                  <p className="text-xs text-gray-500 mt-1">Employee can set Active/Inactive</p>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* Promotion History */}
        <TabsContent value="promotions">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Promotion History</h3>
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <div className="space-y-4">
              {employeeData.promotionHistory.map((promo, index) => (
                <div key={index} className="flex gap-4 pb-4 border-b border-gray-200 last:border-0">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <TrendingUp className="w-6 h-6 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-medium text-gray-900">
                          {promo.from === "-" ? "Initial Position" : `Promoted from ${promo.from} to ${promo.to}`}
                        </p>
                        <p className="text-sm text-gray-600">{promo.reason}</p>
                      </div>
                      <span className="text-sm text-gray-500">{promo.date}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        {/* Commendations */}
        <TabsContent value="commendations">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Commendations & Awards</h3>
              <Award className="w-5 h-5 text-yellow-600" />
            </div>
            <div className="space-y-4">
              {employeeData.commendations.map((comm, index) => (
                <div key={index} className="flex gap-4 pb-4 border-b border-gray-200 last:border-0">
                  <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Award className="w-6 h-6 text-yellow-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-medium text-gray-900">{comm.title}</p>
                        <p className="text-sm text-gray-600">{comm.description}</p>
                        <p className="text-xs text-gray-500 mt-1">Issued by {comm.issuedBy}</p>
                      </div>
                      <span className="text-sm text-gray-500">{comm.date}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        {/* Sanctions */}
        <TabsContent value="sanctions">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Sanctions & Warnings</h3>
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div className="space-y-4">
              {employeeData.sanctions.map((sanction, index) => (
                <div key={index} className="flex gap-4 pb-4 border-b border-gray-200 last:border-0">
                  <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <AlertTriangle className="w-6 h-6 text-red-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-medium text-gray-900">{sanction.type}</p>
                        <p className="text-sm text-gray-600">{sanction.reason}</p>
                        <p className="text-xs text-gray-500 mt-1">Issued by {sanction.issuedBy}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-sm text-gray-500 block">{sanction.date}</span>
                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100 mt-1">
                          {sanction.duration}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
