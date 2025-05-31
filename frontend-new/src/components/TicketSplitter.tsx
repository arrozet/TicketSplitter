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
  is_ticket: boolean;
  error_message: string | null;
  detected_content: string | null;
}

interface SplitShare {
  user_id: string;
  amount_due: number;
  items: Item[];
  shared_items: Item[];
}

interface SplitResult {
  shares: SplitShare[];
  total_calculated: number;
}

interface ItemAssignment {
  item_id: number;
  quantity: number;
}

export default function TicketSplitter() {
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [parsedReceipt, setParsedReceipt] = useState<ParsedReceipt | null>(null);
  const [users, setUsers] = useState<string[]>([]);
  const [newUserName, setNewUserName] = useState('');
  const [userItemSelections, setUserItemSelections] = useState<Record<string, number[]>>({});
  const [splitResult, setSplitResult] = useState<SplitResult | null>(null);
  const [showUnassignedDialog, setShowUnassignedDialog] = useState(false);
  const [unassignedItems, setUnassignedItems] = useState<Item[]>([]);
  const [showInvalidImageDialog, setShowInvalidImageDialog] = useState(false);
  const [invalidImageInfo, setInvalidImageInfo] = useState<{message: string, detected_content?: string} | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatCurrency = (amount: number | null) => {
    return amount !== null && amount !== undefined ? `${parseFloat(amount.toString()).toFixed(2)} €` : '-';
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validar que sea una imagen
      if (!file.type.startsWith('image/')) {
        setError("Por favor selecciona un archivo de imagen válido.");
        return;
      }
      
      setSelectedFile(file);
      setError(null);
      
      // Crear vista previa de la imagen
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
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
        // Si es error 400, probablemente la imagen no es un ticket válido
        if (response.status === 400) {
          setInvalidImageInfo({
            message: errorData.detail || "La imagen no parece ser un ticket válido. Por favor, sube una imagen de un ticket de compra o factura.",
            detected_content: errorData.detected_content
          });
          setShowInvalidImageDialog(true);
          return;
        }
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

  const isItemSelectedByUser = (userName: string, itemId: number): boolean => {
    return userItemSelections[userName]?.includes(itemId) || false;
  };

  const getParticipantsForItem = (itemId: number): string[] => {
    return users.filter(userName => isItemSelectedByUser(userName, itemId));
  };

  const calculateQuantityPerPersonForItem = (itemId: number): number => {
    const participants = getParticipantsForItem(itemId);
    if (participants.length === 0) return 0;
    const item = parsedReceipt?.items.find(i => i.id === itemId);
    return item ? item.quantity / participants.length : 0;
  };

  const getUnassignedItems = (): Item[] => {
    if (!parsedReceipt) return [];
    return parsedReceipt.items.filter(item => getParticipantsForItem(item.id).length === 0);
  };

  const calculateSplit = async () => {
    if (!parsedReceipt) {
      setError("Necesitas subir y procesar un ticket primero.");
      return;
    }

    // Verificar si hay elementos sin asignar
    const unassignedItemsList = getUnassignedItems();
    if (unassignedItemsList.length > 0) {
      setUnassignedItems(unassignedItemsList);
      setShowUnassignedDialog(true);
      return;
    }

    proceedWithCalculation();
  };

  const proceedWithCalculation = async () => {
    if (!parsedReceipt) return;

    // Convertir selecciones a formato de asignaciones con cantidades
    const assignmentsPayload: Record<string, ItemAssignment[]> = {};
    
    users.forEach(userName => {
      const userSelections = userItemSelections[userName] || [];
      assignmentsPayload[userName] = userSelections.map(itemId => {
        const quantity = calculateQuantityPerPersonForItem(itemId);
        return { item_id: itemId, quantity };
      });
    });

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

  const handleUnassignedDialogProceed = () => {
    setShowUnassignedDialog(false);
    proceedWithCalculation();
  };

  const handleUnassignedDialogCancel = () => {
    setShowUnassignedDialog(false);
  };

  const handleInvalidImageDialogClose = () => {
    setShowInvalidImageDialog(false);
    setInvalidImageInfo(null);
    setSelectedFile(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const resetApp = () => {
    setCurrentStep(1);
    setSelectedFile(null);
    setImagePreview(null);
    setParsedReceipt(null);
    setUsers([]);
    setNewUserName('');
    setUserItemSelections({});
    setSplitResult(null);
    setError(null);
    setShowInvalidImageDialog(false);
    setInvalidImageInfo(null);
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
            Ticket Splitter
          </h1>
          <p className="text-xl text-muted-foreground">
            Divide los gastos de tu ticket fácilmente
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
                          Subir ticket o factura
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                          Selecciona o arrastra una imagen de tu ticket.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6 pt-4">
                        <div className="space-y-2">
                          <Label htmlFor="receipt-image" className="text-sm font-medium">Imagen del ticket</Label>
                          <div 
                            className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
                            onClick={() => fileInputRef.current?.click()}
                            onDragOver={(e) => {
                              e.preventDefault();
                              e.currentTarget.classList.add('border-primary', 'bg-primary/5');
                            }}
                            onDragLeave={(e) => {
                              e.preventDefault();
                              e.currentTarget.classList.remove('border-primary', 'bg-primary/5');
                            }}
                            onDrop={(e) => {
                              e.preventDefault();
                              e.currentTarget.classList.remove('border-primary', 'bg-primary/5');
                              const files = e.dataTransfer.files;
                              if (files.length > 0) {
                                const file = files[0];
                                if (file.type.startsWith('image/')) {
                                  setSelectedFile(file);
                                  setError(null);
                                  const reader = new FileReader();
                                  reader.onload = (e) => {
                                    setImagePreview(e.target?.result as string);
                                  };
                                  reader.readAsDataURL(file);
                                } else {
                                  setError("Por favor selecciona un archivo de imagen válido.");
                                }
                              }
                            }}
                          >
                            <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                            <p className="text-sm font-medium mb-2">Arrastra tu ticket aquí o haz clic para seleccionar</p>
                            <p className="text-xs text-muted-foreground">Formatos soportados: JPG, PNG, GIF, WebP</p>
                          </div>
                          <Input
                            id="receipt-image"
                            type="file"
                            accept="image/*"
                            onChange={handleFileSelect}
                            ref={fileInputRef}
                            className="hidden"
                          />
                        </div>
                        {selectedFile && (
                          <div className="space-y-4">
                            <p className="text-sm text-muted-foreground">
                              Archivo: <span className="font-medium text-foreground">{selectedFile.name}</span>
                            </p>
                            {imagePreview && (
                              <div className="border-2 border-border rounded-lg p-4 bg-muted/20">
                                <p className="text-sm font-medium mb-3 text-center">Vista Previa:</p>
                                <div className="flex justify-center">
                                  <img 
                                    src={imagePreview} 
                                    alt="Vista previa del ticket" 
                                    className="max-w-full max-h-80 object-contain rounded-md shadow-md border"
                                  />
                                </div>
                                <p className="text-xs text-muted-foreground text-center mt-2">
                                  Verifica que esta sea la imagen correcta antes de continuar
                                </p>
                                <div className="flex justify-center mt-3">
                                  <Button 
                                    variant="outline" 
                                    size="sm"
                                    onClick={() => {
                                      setSelectedFile(null);
                                      setImagePreview(null);
                                      if (fileInputRef.current) {
                                        fileInputRef.current.value = '';
                                      }
                                    }}
                                    className="text-xs"
                                  >
                                    Cambiar Imagen
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
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
                              <Upload className="h-5 w-5 mr-2" /> Subir y procesar
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
                          Artículos del ticket
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
                            Continuar a asignación
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
                          Asignar artículos
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                          Añade personas y luego asigna quién ha consumido cada artículo. Los artículos se dividirán automáticamente entre los participantes.
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
                          <div className="space-y-4">
                            {parsedReceipt.items.map((item) => {
                              const participants = getParticipantsForItem(item.id);
                              const quantityPerPerson = calculateQuantityPerPersonForItem(item.id);
                              
                              return (
                                <Card key={item.id} className="overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-300">
                                  <CardHeader className="bg-muted/30 p-4">
                                    <div className="flex justify-between items-start">
                                      <div className="flex-grow">
                                        <CardTitle className="text-lg font-semibold">{item.name}</CardTitle>
                                        <p className="text-sm text-muted-foreground mt-1">
                                          {item.quantity} unidades × {formatCurrency(item.price)} = {formatCurrency(item.total_price)}
                                        </p>
                                        {participants.length > 0 && (
                                          <p className="text-sm text-blue-600 mt-2">
                                            {participants.length} participantes → {quantityPerPerson.toFixed(2)} unidades c/u
                                          </p>
                                        )}
                                      </div>
                                      <Badge variant={participants.length > 0 ? "default" : "secondary"} className="ml-4">
                                        {participants.length > 0 ? `${participants.length} personas` : "Sin asignar"}
                                      </Badge>
                                    </div>
                                  </CardHeader>
                                  <CardContent className="p-4">
                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                      {users.map((userName) => {
                                        const isSelected = isItemSelectedByUser(userName, item.id);
                                        return (
                                          <label 
                                            key={userName} 
                                            className={`flex items-center space-x-2 p-3 rounded-md border cursor-pointer transition-all ${
                                              isSelected 
                                                ? 'border-primary bg-primary/10 text-primary' 
                                                : 'border-border hover:border-primary/50 hover:bg-muted/50'
                                            }`}
                                          >
                                            <input
                                              type="checkbox"
                                              checked={isSelected}
                                              onChange={() => toggleItemForUser(userName, item.id)}
                                              className="form-checkbox h-4 w-4 text-primary rounded border focus:ring-primary transition-all"
                                            />
                                            <span className="text-sm font-medium">{userName}</span>
                                          </label>
                                        );
                                      })}
                                    </div>
                                    {participants.length === 0 && (
                                      <p className="text-sm text-orange-600 text-center mt-3 italic">
                                        ⚠️ Este artículo se dividirá equitativamente entre todas las personas
                                      </p>
                                    )}
                                  </CardContent>
                                </Card>
                              );
                            })}
                          </div>
                        ) : (
                            <div className="text-center py-10 text-muted-foreground">
                                <Users size={48} className="mx-auto mb-4 opacity-50" />
                                Añade personas para empezar a asignar artículos.
                            </div>
                        )}
                        
                        {/* Resumen general */}
                        {users.length > 0 && parsedReceipt && (
                          <Card className="mt-8 bg-gradient-to-r from-muted/20 to-muted/10">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-lg flex items-center gap-2">
                                <Calculator className="h-5 w-5" />
                                Resumen de asignaciones
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                                <div className="p-4 rounded-lg bg-background border">
                                  <div className="text-2xl font-bold text-green-600">
                                    {parsedReceipt.items.filter(item => getParticipantsForItem(item.id).length > 0).length}
                                  </div>
                                  <div className="text-sm text-muted-foreground">Artículos Asignados</div>
                                </div>
                                <div className="p-4 rounded-lg bg-background border">
                                  <div className="text-2xl font-bold text-orange-600">
                                    {getUnassignedItems().length}
                                  </div>
                                  <div className="text-sm text-muted-foreground">Sin Asignar</div>
                                </div>
                                <div className="p-4 rounded-lg bg-background border">
                                  <div className="text-2xl font-bold text-primary">
                                    {users.length}
                                  </div>
                                  <div className="text-sm text-muted-foreground">Personas</div>
                                </div>
                              </div>
                              {getUnassignedItems().length > 0 && (
                                <div className="mt-4 p-3 rounded-md bg-orange-50 border border-orange-200">
                                  <p className="text-sm font-medium text-orange-800 mb-1">
                                    ⚠️ Artículos que se dividirán equitativamente:
                                  </p>
                                  <p className="text-xs text-orange-700">
                                    {getUnassignedItems().map(item => item.name).join(', ')}
                                  </p>
                                </div>
                              )}
                            </CardContent>
                          </Card>
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
                                <Calculator className="h-5 w-5 mr-2" /> Calcular división
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
                          Resultados de la división
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
                              <TableHead>Artículos asignados</TableHead>
                              <TableHead className="text-right">Total a pagar</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {splitResult.shares.map((share) => (
                              <TableRow key={share.user_id} className="hover:bg-muted/50 transition-colors">
                                <TableCell className="font-semibold py-3">{share.user_id}</TableCell>
                                <TableCell className="py-3">
                                  <div className="space-y-2">
                                    {/* Artículos asignados específicamente */}
                                    {share.items.length > 0 && (
                                      <div>
                                        <div className="text-xs font-medium text-green-700 mb-1">Artículos asignados:</div>
                                        <ul className="list-disc list-inside space-y-1 text-xs">
                                          {share.items.map((item) => (
                                            <li key={`assigned-${item.id}`} className="text-green-800">
                                              {item.name} - Cantidad: {item.quantity} ({formatCurrency(item.total_price)})
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                    
                                    {/* Artículos compartidos (no asignados) */}
                                    {share.shared_items && share.shared_items.length > 0 && (
                                      <div>
                                        <div className="text-xs font-medium text-orange-700 mb-1">Artículos compartidos:</div>
                                        <ul className="list-disc list-inside space-y-1 text-xs">
                                          {share.shared_items.map((item) => (
                                            <li key={`shared-${item.id}`} className="text-orange-800">
                                              {item.name} - Cantidad: {item.quantity} ({formatCurrency(item.total_price)}) 
                                              <span className="text-muted-foreground italic"> - dividido equitativamente</span>
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                    
                                    {/* Mensaje si no hay artículos */}
                                    {share.items.length === 0 && (!share.shared_items || share.shared_items.length === 0) && (
                                      <span className="text-muted-foreground italic">Solo costos adicionales (impuestos/propinas)</span>
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell className="text-right font-bold text-lg py-3">
                                  {formatCurrency(share.amount_due)}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                        <div className="mt-8 pt-6 border-t border text-right">
                          <p className="text-muted-foreground">Total calculado:</p>
                          <p className="text-2xl font-bold text-primary">
                            {formatCurrency(splitResult.total_calculated)}
                          </p>
                        </div>
                        <div className="mt-10 flex justify-center">
                          <Button onClick={resetApp} variant="outline" className="text-base py-3 px-8 transition-transform transform hover:scale-105">
                            <RotateCcw className="h-4 w-4 mr-2" /> Procesar otro ticket
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

        {/* Diálogo de artículos no asignados */}
        {showUnassignedDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md shadow-2xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl text-orange-600">
                  <AlertCircle className="h-6 w-6" />
                  Artículos sin asignar
                </CardTitle>
                <CardDescription>
                  Los siguientes artículos no han sido asignados a ninguna persona:
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-orange-50 border border-orange-200 rounded-md p-3">
                  <ul className="space-y-1">
                    {unassignedItems.map((item) => (
                      <li key={item.id} className="text-sm">
                        <span className="font-medium">{item.name}</span>
                        <span className="text-muted-foreground"> - {item.quantity} unidades ({formatCurrency(item.total_price)})</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <p className="text-sm text-muted-foreground">
                  ¿Deseas continuar? Los artículos no asignados se dividirán equitativamente entre todas las personas.
                </p>
                <div className="flex gap-3 justify-end">
                  <Button 
                    variant="outline" 
                    onClick={handleUnassignedDialogCancel}
                    className="transition-transform transform hover:scale-105"
                  >
                    Cancelar
                  </Button>
                  <Button 
                    onClick={handleUnassignedDialogProceed}
                    className="transition-transform transform hover:scale-105"
                  >
                    Continuar
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Diálogo de imagen inválida */}
        {showInvalidImageDialog && invalidImageInfo && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-lg shadow-2xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl text-red-600">
                  <AlertCircle className="h-6 w-6" />
                  Imagen No Válida
                </CardTitle>
                <CardDescription>
                  La imagen que has subido no es un ticket de compra o factura.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <p className="text-sm text-red-800 font-medium mb-2">
                    {invalidImageInfo.message}
                  </p>
                  {invalidImageInfo.detected_content && (
                    <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
                      <p className="text-xs text-blue-700 font-medium mb-1">
                        🔍 Hemos detectado que es:
                      </p>
                      <p className="text-sm text-blue-800">
                        {invalidImageInfo.detected_content}
                      </p>
                    </div>
                  )}
                </div>
                <div className="bg-green-50 border border-green-200 rounded-md p-3">
                  <p className="text-sm text-green-800">
                    <span className="font-medium">💡 Consejo:</span> Sube una foto clara de un ticket de compra, factura o recibo que contenga:
                  </p>
                  <ul className="list-disc list-inside text-xs text-green-700 mt-2 space-y-1">
                    <li>Lista de artículos con precios</li>
                    <li>Subtotal, impuestos y total</li>
                    <li>Información del establecimiento</li>
                  </ul>
                </div>
                <div className="flex gap-3 justify-end pt-4">
                  <Button 
                    onClick={handleInvalidImageDialogClose}
                    className="transition-transform transform hover:scale-105"
                  >
                    Entendido, subir otra imagen
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

      </div>
    </div>
  );
} 