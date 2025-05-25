import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload, Users, Calculator, Receipt, AlertCircle, CheckCircle2, RotateCcw } from 'lucide-react';

const API_BASE_URL = "http://localhost:8000/api/v1/receipts";

interface Item {
  id: number;
  name: string;
  quantity: number;
  price: number;
  total_price: number;
}

interface ParsedReceipt {
  receipt_id: string;
  filename: string;
  items: Item[];
  subtotal: number | null;
  tax: number | null;
  total: number | null;
  raw_text: string;
}

interface SplitShare {
  user_id: string;
  amount_due: number;
  items: Item[];
}

interface SplitResult {
  shares: SplitShare[];
  total_calculated: number;
}

export default function TicketSplitter() {
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parsedReceipt, setParsedReceipt] = useState<ParsedReceipt | null>(null);
  const [users, setUsers] = useState<string[]>([]);
  const [newUserName, setNewUserName] = useState('');
  const [userItemSelections, setUserItemSelections] = useState<Record<string, number[]>>({});
  const [splitResult, setSplitResult] = useState<SplitResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatCurrency = (amount: number | null) => {
    return amount !== null && amount !== undefined ? `${parseFloat(amount.toString()).toFixed(2)} €` : '-';
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Por favor selecciona una imagen del ticket.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Error desconocido al subir." }));
        throw new Error(`Error ${response.status}: ${errorData.detail}`);
      }
      const data = await response.json();
      setParsedReceipt(data);
      setCurrentStep(2);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Hubo un problema procesando el ticket.");
    } finally {
      setIsLoading(false);
    }
  };

  const addUser = () => {
    if (!newUserName.trim()) {
      setError("Por favor ingresa un nombre para la persona.");
      return;
    }
    if (users.includes(newUserName.trim())) {
      setError(`La persona '${newUserName}' ya ha sido añadida.`);
      return;
    }
    setError(null);
    const userName = newUserName.trim();
    setUsers([...users, userName]);
    setUserItemSelections({ ...userItemSelections, [userName]: [] });
    setNewUserName('');
  };

  const toggleItemForUser = (userName: string, itemId: number) => {
    const currentSelections = userItemSelections[userName] || [];
    const newSelections = currentSelections.includes(itemId)
      ? currentSelections.filter(id => id !== itemId)
      : [...currentSelections, itemId];
    setUserItemSelections({
      ...userItemSelections,
      [userName]: newSelections
    });
  };

  const calculateSplit = async () => {
    if (!parsedReceipt) {
      setError("Necesitas subir y procesar un ticket primero.");
      return;
    }
    const assignmentsPayload = Object.entries(userItemSelections)
      .filter(([_, itemIds]) => itemIds.length > 0)
      .reduce((obj, [key, value]) => {
        obj[key] = value;
        return obj;
      }, {} as Record<string, number[]>);
    if (Object.keys(assignmentsPayload).length === 0 && users.length > 0) {
      users.forEach(name => {
        if (!assignmentsPayload[name]) assignmentsPayload[name] = [];
      });
    } else if (Object.keys(assignmentsPayload).length === 0) {
      setError("Por favor añade personas para asignar artículos o dividir costos comunes.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/${parsedReceipt.receipt_id}/split`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_item_assignments: assignmentsPayload }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Error desconocido durante el cálculo." }));
        throw new Error(`Error ${response.status}: ${errorData.detail}`);
      }
      const results = await response.json();
      setSplitResult(results);
      setCurrentStep(4);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Hubo un problema calculando la división.");
    } finally {
      setIsLoading(false);
    }
  };

  const resetApp = () => {
    setCurrentStep(1);
    setSelectedFile(null);
    setParsedReceipt(null);
    setUsers([]);
    setNewUserName('');
    setUserItemSelections({});
    setSplitResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans transition-colors duration-300">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold tracking-tight text-primary mb-3">
            TicketSplitter
          </h1>
          <p className="text-xl text-muted-foreground">
            Divide los gastos de tu ticket fácilmente.
          </p>
        </header>

        {/* Progress Steps - Minimalista */}
        <div className="flex justify-center mb-12">
          <div className="flex items-center space-x-2 sm:space-x-4">
            {[1, 2, 3, 4].map((step, index) => (
              <React.Fragment key={step}>
                <div className={`relative flex flex-col items-center transition-all duration-300 ${
                  currentStep >= step ? 'text-primary' : 'text-muted-foreground'
                }`}>
                  <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-sm font-medium border-2 ${
                    currentStep >= step 
                      ? 'bg-primary text-primary-foreground border-primary' 
                      : 'bg-muted border'
                  }`}>
                    {currentStep > step ? <CheckCircle2 size={20} /> : step}
                  </div>
                  <p className="text-xs sm:text-sm mt-2 text-center whitespace-nowrap">
                    {['Subir', 'Revisar', 'Asignar', 'Resultado'][index]}
                  </p>
                </div>
                {step < 4 && (
                  <div className={`flex-1 h-1 rounded transition-colors duration-500 ${
                    currentStep > step ? 'bg-primary' : 'bg-border'
                  }`} style={{ minWidth: '20px', maxWidth: '60px' }} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-8 max-w-2xl mx-auto shadow-md transition-all duration-300 ease-out transform scale-100 hover:scale-105">
            <AlertCircle className="h-5 w-5" />
            <AlertDescription>
              {error}
            </AlertDescription>
          </Alert>
        )}

        {/* Animated Card Container - Para transiciones entre pasos */}
        <div className="relative max-w-3xl mx-auto">
          {[1, 2, 3, 4].map((stepNum) => (
            <div
              key={stepNum}
              className={`absolute w-full transition-all duration-500 ease-in-out transform ${
                currentStep === stepNum
                  ? 'opacity-100 translate-y-0'
                  : 'opacity-0 -translate-y-10 pointer-events-none'
              }`}
            >
              {currentStep === stepNum && (
                <Card className="shadow-xl border/60 backdrop-blur-sm bg-card/80">
                  {/* Step 1: Upload */}
                  {stepNum === 1 && (
                    <>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-2xl">
                          <Upload className="h-6 w-6 text-primary" />
                          Subir Ticket
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                          Selecciona o arrastra una imagen de tu ticket.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6 pt-4">
                        <div className="space-y-2">
                          <Label htmlFor="receipt-image" className="text-sm font-medium">Imagen del Ticket</Label>
                          <Input
                            id="receipt-image"
                            type="file"
                            accept="image/*"
                            onChange={handleFileSelect}
                            ref={fileInputRef}
                            className="file:text-primary-foreground file:bg-primary hover:file:bg-primary/90 transition-colors"
                          />
                        </div>
                        {selectedFile && (
                          <p className="text-sm text-muted-foreground">
                            Archivo: <span className="font-medium text-foreground">{selectedFile.name}</span>
                          </p>
                        )}
                        <Button 
                          onClick={handleUpload} 
                          disabled={!selectedFile || isLoading}
                          className="w-full text-base py-3 transition-all duration-200 ease-in-out transform hover:scale-105 active:scale-95"
                          variant={isLoading ? "secondary" : "default"}
                        >
                          {isLoading ? (
                            <>
                              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"></div>
                              Procesando...
                            </>
                          ) : (
                            <>
                              <Upload className="h-5 w-5 mr-2" /> Subir y Procesar
                            </>
                          )}
                        </Button>
                        {isLoading && (
                          <Progress value={undefined} className="w-full h-2 [&>div]:bg-primary transition-all" />
                        )}
                      </CardContent>
                    </>
                  )}
                  {/* Step 2: Review Items */}
                  {stepNum === 2 && parsedReceipt && (
                    <>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-2xl">
                          <Receipt className="h-6 w-6 text-primary" />
                          Artículos del Ticket
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                          Ticket ID: <Badge variant="outline" className="font-mono text-xs">{parsedReceipt.receipt_id}</Badge>
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        {parsedReceipt.items.length > 0 ? (
                          <Table className="text-sm">
                            <TableHeader>
                              <TableRow>
                                <TableHead className="w-[50px]">ID</TableHead>
                                <TableHead>Descripción</TableHead>
                                <TableHead className="text-center">Cant.</TableHead>
                                <TableHead className="text-right">P. Unit.</TableHead>
                                <TableHead className="text-right">Total</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {parsedReceipt.items.map((item) => (
                                <TableRow key={item.id} className="hover:bg-muted/50 transition-colors">
                                  <TableCell className="font-mono text-xs">{item.id}</TableCell>
                                  <TableCell className="font-medium">{item.name}</TableCell>
                                  <TableCell className="text-center">{item.quantity}</TableCell>
                                  <TableCell className="text-right">{formatCurrency(item.price)}</TableCell>
                                  <TableCell className="text-right font-semibold">{formatCurrency(item.total_price)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        ) : (
                          <div className="text-center py-10 text-muted-foreground">
                            <Receipt size={48} className="mx-auto mb-4 opacity-50" />
                            No se encontraron artículos en el ticket.
                          </div>
                        )}
                        <div className="grid grid-cols-3 gap-4 mt-8 pt-6 border-t border text-sm">
                          <div><span className="font-medium text-muted-foreground">Subtotal:</span> {formatCurrency(parsedReceipt.subtotal)}</div>
                          <div><span className="font-medium text-muted-foreground">Impuestos:</span> {formatCurrency(parsedReceipt.tax)}</div>
                          <div className="font-semibold"><span className="font-medium text-muted-foreground">Total:</span> {formatCurrency(parsedReceipt.total)}</div>
                        </div>
                        <div className="mt-8 flex justify-end">
                          <Button onClick={() => setCurrentStep(3)} className="text-base py-3 px-6 transition-transform transform hover:scale-105">
                            Continuar a Asignación
                          </Button>
                        </div>
                      </CardContent>
                    </>
                  )}
                  {/* Step 3: Assign Items */}
                  {stepNum === 3 && parsedReceipt && (
                    <>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-2xl">
                          <Users className="h-6 w-6 text-primary" />
                          Asignar Artículos
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                          Añade personas y asigna artículos a cada una.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex gap-3 mb-8">
                          <Input
                            placeholder="Nombre de la persona"
                            value={newUserName}
                            onChange={(e) => setNewUserName(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && addUser()}
                            className="text-base"
                          />
                          <Button onClick={addUser} variant="outline" className="transition-transform transform hover:scale-105">
Añadir
                          </Button>
                        </div>
                        {users.length > 0 ? (
                          <div className="space-y-6">
                            {users.map((userName) => (
                              <Card key={userName} className="overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-300">
                                <CardHeader className="bg-muted/30 p-4">
                                  <CardTitle className="text-lg font-semibold">{userName}</CardTitle>
                                </CardHeader>
                                <CardContent className="p-4 space-y-2">
                                  {parsedReceipt.items.map((item) => (
                                    <label key={item.id} className="flex items-center space-x-3 p-2 rounded-md hover:bg-muted/50 cursor-pointer transition-colors">
                                      <input
                                        type="checkbox"
                                        checked={userItemSelections[userName]?.includes(item.id) || false}
                                        onChange={() => toggleItemForUser(userName, item.id)}
                                        className="form-checkbox h-5 w-5 text-primary rounded border focus:ring-primary transition-all"
                                      />
                                      <span className="text-sm flex-grow">{item.name}</span>
                                      <span className="text-xs font-mono text-muted-foreground">{formatCurrency(item.total_price)}</span>
                                    </label>
                                  ))}
                                  {parsedReceipt.items.length === 0 && <p className="text-sm text-muted-foreground italic">No hay artículos para asignar.</p>}
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        ) : (
                            <div className="text-center py-10 text-muted-foreground">
                                <Users size={48} className="mx-auto mb-4 opacity-50" />
                                Añade personas para empezar a asignar artículos.
                            </div>
                        )}
                        <div className="mt-8 flex justify-end">
                          <Button 
                            onClick={calculateSplit} 
                            disabled={users.length === 0 || isLoading}
                            className="text-base py-3 px-6 transition-all duration-200 ease-in-out transform hover:scale-105 active:scale-95"
                            variant={isLoading ? "secondary" : "default"}
                          >
                            {isLoading ? (
                              <>
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"></div>
                                Calculando...
                              </>
                            ) : (
                              <>
                                <Calculator className="h-5 w-5 mr-2" /> Calcular División
                              </>
                            )}
                          </Button>
                        </div>
                      </CardContent>
                    </>
                  )}
                  {/* Step 4: Results */}
                  {stepNum === 4 && splitResult && (
                     <>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-2xl">
                          <CheckCircle2 className="h-6 w-6 text-green-500" />
                          Resultados de la División
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                          ¡Listo! Aquí está cuánto debe pagar cada persona.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <Table className="text-sm">
                          <TableHeader>
                            <TableRow>
                              <TableHead>Persona</TableHead>
                              <TableHead>Artículos Asignados</TableHead>
                              <TableHead className="text-right">Total a Pagar</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {splitResult.shares.map((share) => (
                              <TableRow key={share.user_id} className="hover:bg-muted/50 transition-colors">
                                <TableCell className="font-semibold py-3">{share.user_id}</TableCell>
                                <TableCell className="py-3">
                                  {share.items.length > 0 ? (
                                    <ul className="list-disc list-inside space-y-1 text-xs">
                                      {share.items.map((item) => (
                                        <li key={item.id}>
                                          {item.name} ({formatCurrency(item.total_price)})
                                        </li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <span className="text-muted-foreground italic">Costos compartidos / Sin asignación específica</span>
                                  )}
                                </TableCell>
                                <TableCell className="text-right font-bold text-lg py-3">
                                  {formatCurrency(share.amount_due)}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                        <div className="mt-8 pt-6 border-t border text-right">
                          <p className="text-muted-foreground">Total Calculado:</p>
                          <p className="text-2xl font-bold text-primary">
                            {formatCurrency(splitResult.total_calculated)}
                          </p>
                        </div>
                        <div className="mt-10 flex justify-center">
                          <Button onClick={resetApp} variant="outline" className="text-base py-3 px-8 transition-transform transform hover:scale-105">
                            <RotateCcw className="h-4 w-4 mr-2" /> Procesar Otro Ticket
                          </Button>
                        </div>
                      </CardContent>
                    </>
                  )}
                </Card>
              )}
            </div>
          ))}
        </div>

      </div>
    </div>
  );
} 