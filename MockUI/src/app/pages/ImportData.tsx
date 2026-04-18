import { useState } from "react";
import { Upload, Download, FileSpreadsheet, CheckCircle, XCircle, AlertTriangle, Info } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

const sampleData = [
  { row: 1, name: "John Doe", email: "john@company.com", department: "IT", level: "L6", status: "Valid", issues: [] },
  { row: 2, name: "Jane Smith", email: "jane@company.com", department: "HR", level: "L5", status: "Valid", issues: [] },
  { row: 3, name: "Bob Johnson", email: "invalid-email", department: "Finance", level: "L9", status: "Error", issues: ["Invalid email", "Invalid level"] },
  { row: 4, name: "", email: "empty@company.com", department: "IT", level: "L7", status: "Error", issues: ["Missing name"] },
  { row: 5, name: "Alice Williams", email: "alice@company.com", department: "Marketing", level: "L6", status: "Warning", issues: ["Department not in system"] },
];

export function ImportData() {
  const [step, setStep] = useState<"upload" | "validate" | "complete">("upload");
  const [fileName, setFileName] = useState("");

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      // Simulate validation
      setTimeout(() => setStep("validate"), 1000);
    }
  };

  const handleImport = () => {
    setStep("complete");
  };

  const validCount = sampleData.filter(d => d.status === "Valid").length;
  const errorCount = sampleData.filter(d => d.status === "Error").length;
  const warningCount = sampleData.filter(d => d.status === "Warning").length;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Import Employee Data</h1>
        <p className="text-gray-600">Bulk import employee records from CSV or Excel files</p>
      </div>

      {/* Steps */}
      <div className="mb-8">
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 ${step === "upload" ? "text-blue-600" : "text-gray-400"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step === "upload" ? "bg-blue-600 text-white" : "bg-gray-200"
            }`}>
              1
            </div>
            <span className="font-medium">Upload File</span>
          </div>
          <div className="flex-1 h-px bg-gray-200"></div>
          <div className={`flex items-center gap-2 ${step === "validate" ? "text-blue-600" : "text-gray-400"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step === "validate" ? "bg-blue-600 text-white" : "bg-gray-200"
            }`}>
              2
            </div>
            <span className="font-medium">Validate Data</span>
          </div>
          <div className="flex-1 h-px bg-gray-200"></div>
          <div className={`flex items-center gap-2 ${step === "complete" ? "text-blue-600" : "text-gray-400"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step === "complete" ? "bg-blue-600 text-white" : "bg-gray-200"
            }`}>
              3
            </div>
            <span className="font-medium">Complete</span>
          </div>
        </div>
      </div>

      {/* Upload Step */}
      {step === "upload" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card className="p-12">
              <div className="text-center">
                <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Upload className="w-10 h-10 text-blue-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload Employee Data File</h3>
                <p className="text-gray-600 mb-6">Supported formats: CSV, XLSX</p>
                
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Button type="button" size="lg" className="gap-2">
                    <Upload className="w-5 h-5" />
                    Choose File
                  </Button>
                </label>

                <div className="mt-8 pt-8 border-t border-gray-200">
                  <Button variant="outline" className="gap-2">
                    <Download className="w-4 h-4" />
                    Download Template File
                  </Button>
                  <p className="text-sm text-gray-500 mt-2">Use our template to ensure proper formatting</p>
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="p-6 bg-blue-50 border-blue-200">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-blue-900 mb-2">Required Columns</h4>
                  <div className="space-y-1 text-sm text-blue-800">
                    <p>• First Name</p>
                    <p>• Last Name</p>
                    <p>• Email</p>
                    <p>• Department</p>
                    <p>• Position</p>
                    <p>• Degree (BSc/MSc/PhD)</p>
                    <p>• Join Date</p>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="p-6 bg-yellow-50 border-yellow-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-yellow-900 mb-2">Data Cleaning Guide</h4>
                  <div className="space-y-1 text-sm text-yellow-800">
                    <p>• Remove duplicate entries</p>
                    <p>• Validate email formats</p>
                    <p>• Use standard department names</p>
                    <p>• Ensure dates are in YYYY-MM-DD format</p>
                    <p>• Check degree values (BSc/MSc/PhD only)</p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Validate Step */}
      {step === "validate" && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <FileSpreadsheet className="w-8 h-8 text-blue-600" />
                <div>
                  <p className="text-sm text-gray-600">Total Rows</p>
                  <p className="text-2xl font-bold text-gray-900">{sampleData.length}</p>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-sm text-gray-600">Valid</p>
                  <p className="text-2xl font-bold text-green-600">{validCount}</p>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-8 h-8 text-yellow-600" />
                <div>
                  <p className="text-sm text-gray-600">Warnings</p>
                  <p className="text-2xl font-bold text-yellow-600">{warningCount}</p>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <XCircle className="w-8 h-8 text-red-600" />
                <div>
                  <p className="text-sm text-gray-600">Errors</p>
                  <p className="text-2xl font-bold text-red-600">{errorCount}</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Validation Results */}
          <Card>
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Validation Results</h3>
                  <p className="text-sm text-gray-600 mt-1">File: {fileName}</p>
                </div>
                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setStep("upload")}>
                    Upload Different File
                  </Button>
                  <Button 
                    onClick={handleImport}
                    disabled={errorCount > 0}
                    className="gap-2"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Import Valid Rows ({validCount})
                  </Button>
                </div>
              </div>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Row</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Level</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Issues</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sampleData.map((row) => (
                  <TableRow key={row.row}>
                    <TableCell>{row.row}</TableCell>
                    <TableCell>{row.name || <span className="text-gray-400">Empty</span>}</TableCell>
                    <TableCell>{row.email}</TableCell>
                    <TableCell>{row.department}</TableCell>
                    <TableCell>{row.level}</TableCell>
                    <TableCell>
                      <Badge
                        className={
                          row.status === "Valid"
                            ? "bg-green-100 text-green-700 hover:bg-green-100"
                            : row.status === "Warning"
                            ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-100"
                            : "bg-red-100 text-red-700 hover:bg-red-100"
                        }
                      >
                        {row.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {row.issues.length > 0 ? (
                        <div className="text-sm text-red-600">
                          {row.issues.join(", ")}
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* Complete Step */}
      {step === "complete" && (
        <Card className="p-12">
          <div className="text-center max-w-md mx-auto">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-2">Import Successful!</h3>
            <p className="text-gray-600 mb-8">
              Successfully imported {validCount} employee records to the system.
            </p>
            
            <div className="space-y-3">
              <Button className="w-full" onClick={() => window.location.href = "/employees"}>
                View Imported Employees
              </Button>
              <Button variant="outline" className="w-full" onClick={() => setStep("upload")}>
                Import More Data
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
