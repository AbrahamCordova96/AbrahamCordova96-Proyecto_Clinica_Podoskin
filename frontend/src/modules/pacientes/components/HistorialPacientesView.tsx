import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { MagnifyingGlass, Plus, User, Phone, EnvelopeSimple, MapPin, IdentificationCard, CalendarBlank, Printer } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { usePacientesStore } from '../stores/pacientesStore'
import { calculateAge } from '../utils/pacientes.utils'
import { ESTADOS_MEXICO, getCURPValidationMessage } from '../constants/nom024-catalogos'
import { imprimirExpediente } from '../utils/expediente-impresion'
import type { Paciente, TratamientoEstado, TratamientoCreateInput, EvolucionCreateInput, PacienteCreateInput } from '../types/pacientes.types'

export function HistorialPacientesView() {
  const {
    pacientes,
    selectedPaciente,
    tratamientos,
    evoluciones,
    podologos,
    isLoading,
    fetchPacientes,
    fetchPaciente,
    createPaciente,
    updatePaciente,
    fetchTratamientos,
    createTratamiento,
    updateTratamiento,
    fetchEvoluciones,
    createEvolucion,
    fetchPodologos,
    setSelectedPaciente
  } = usePacientesStore()

  // Load initial data
  useEffect(() => {
    fetchPacientes()
    fetchPodologos()
  }, [])

  // Load tratamientos when paciente is selected
  useEffect(() => {
    if (selectedPaciente) {
      fetchTratamientos(selectedPaciente.id_paciente)
    }
  }, [selectedPaciente])

  const [searchTerm, setSearchTerm] = useState('')
  const filteredPacientes = pacientes.filter((p: Paciente) => {
    const term = searchTerm.toLowerCase()
    return (
      p.nombres.toLowerCase().includes(term) ||
      p.apellidos.toLowerCase().includes(term) ||
      p.documento_id?.toLowerCase().includes(term) ||
      p.telefono.includes(term)
    )
  })

  const [isCreateMode, setIsCreateMode] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)
  const [showTratamientoModal, setShowTratamientoModal] = useState(false)
  const [showEvolucionModal, setShowEvolucionModal] = useState(false)
  const [selectedTratamiento, setSelectedTratamiento] = useState<any>(null)

  const [formData, setFormData] = useState<PacienteCreateInput>({
    nombres: '',
    apellidos: '',
    fecha_nacimiento: '',
    sexo: '',
    telefono: '',
    email: '',
    domicilio: '',
    documento_id: '',
    // NOM-024 optional fields
    curp: '',
    estado_nacimiento: '',
    nacionalidad: 'MEX',
    estado_residencia: '',
    municipio_residencia: '',
    localidad_residencia: ''
  })

  const [tratamientoForm, setTratamientoForm] = useState<TratamientoCreateInput>({
    paciente_id: 0,
    problema: '',
    fecha_inicio: '',
    fecha_fin: '',
    estado: 'activo',
    notas_adicionales: ''
  })

  const [evolucionForm, setEvolucionForm] = useState<EvolucionCreateInput>({
    tratamiento_id: 0,
    podologo_id: 0,
    fecha_visita: '',
    nota: '',
    tipo_visita: '',
    signos_vitales: {},
    // NOM-024 optional fields
    diagnostico_codigo_cie10: '',
    procedimiento_codigo: ''
  })

  const handleViewPaciente = (paciente: Paciente) => {
    setSelectedPaciente(paciente)
  }

  const handleCreatePaciente = () => {
    setFormData({
      nombres: '',
      apellidos: '',
      fecha_nacimiento: '',
      sexo: '',
      telefono: '',
      email: '',
      domicilio: '',
      documento_id: '',
      // NOM-024 optional fields
      curp: '',
      estado_nacimiento: '',
      nacionalidad: 'MEX',
      estado_residencia: '',
      municipio_residencia: '',
      localidad_residencia: ''
    })
    setIsCreateMode(true)
  }

  const handleEditPaciente = () => {
    if (!selectedPaciente) return
    setFormData({
      nombres: selectedPaciente.nombres,
      apellidos: selectedPaciente.apellidos,
      fecha_nacimiento: selectedPaciente.fecha_nacimiento,
      sexo: selectedPaciente.sexo,
      telefono: selectedPaciente.telefono,
      email: selectedPaciente.email || '',
      domicilio: selectedPaciente.domicilio || '',
      documento_id: selectedPaciente.documento_id || '',
      // NOM-024 optional fields
      curp: selectedPaciente.curp || '',
      estado_nacimiento: selectedPaciente.estado_nacimiento || '',
      nacionalidad: selectedPaciente.nacionalidad || 'MEX',
      estado_residencia: selectedPaciente.estado_residencia || '',
      municipio_residencia: selectedPaciente.municipio_residencia || '',
      localidad_residencia: selectedPaciente.localidad_residencia || ''
    })
    setIsEditMode(true)
  }

  const handleSavePaciente = async () => {
    // Validate CURP if provided
    if (formData.curp) {
      const curpError = getCURPValidationMessage(formData.curp.toUpperCase())
      if (curpError) {
        toast.warning(curpError + ' (campo opcional)')
        // Don't block save, just warn
      }
    }
    
    if (isEditMode && selectedPaciente) {
      const result = await updatePaciente(selectedPaciente.id_paciente, formData)
      if (result) {
        toast.success('Paciente actualizado exitosamente')
        setIsEditMode(false)
      } else {
        toast.error('Error al actualizar paciente')
      }
    } else if (isCreateMode) {
      if (!formData.nombres || !formData.apellidos || !formData.fecha_nacimiento) {
        toast.error('Complete los campos requeridos')
        return
      }
      const result = await createPaciente(formData)
      if (result) {
        toast.success('Paciente creado exitosamente')
        setIsCreateMode(false)
        setSelectedPaciente(result)
      } else {
        toast.error('Error al crear paciente')
      }
    }
  }

  const handleAddTratamiento = () => {
    if (!selectedPaciente) return
    setTratamientoForm({
      paciente_id: selectedPaciente.id_paciente,
      problema: '',
      fecha_inicio: new Date().toISOString().split('T')[0],
      fecha_fin: '',
      estado: 'activo',
      notas_adicionales: ''
    })
    setShowTratamientoModal(true)
  }

  const handleSaveTratamiento = async () => {
    if (!tratamientoForm.problema || !tratamientoForm.fecha_inicio) {
      toast.error('Complete los campos requeridos')
      return
    }
    const result = await createTratamiento(tratamientoForm)
    if (result) {
      toast.success('Tratamiento creado exitosamente')
      setShowTratamientoModal(false)
      if (selectedPaciente) {
        fetchTratamientos(selectedPaciente.id_paciente)
      }
    } else {
      toast.error('Error al crear tratamiento')
    }
  }

  const handleAddEvolucion = (tratamiento: any) => {
    setSelectedTratamiento(tratamiento)
    setEvolucionForm({
      tratamiento_id: tratamiento.id_tratamiento,
      podologo_id: 0,
      fecha_visita: new Date().toISOString().split('T')[0],
      nota: '',
      tipo_visita: '',
      signos_vitales: {},
      // NOM-024 optional fields
      diagnostico_codigo_cie10: '',
      procedimiento_codigo: ''
    })
    setShowEvolucionModal(true)
  }

  const handleSaveEvolucion = async () => {
    if (!evolucionForm.nota || !evolucionForm.podologo_id) {
      toast.error('Complete los campos requeridos')
      return
    }
    const result = await createEvolucion(evolucionForm)
    if (result) {
      toast.success('Evolución registrada exitosamente')
      setShowEvolucionModal(false)
      if (selectedTratamiento) {
        fetchEvoluciones(selectedTratamiento.id_tratamiento)
      }
      if (selectedPaciente) {
        fetchTratamientos(selectedPaciente.id_paciente)
      }
    } else {
      toast.error('Error al registrar evolución')
    }
  }

  const pacienteTratamientos = selectedPaciente
    ? tratamientos.filter((t: any) => t.paciente_id === selectedPaciente.id_paciente)
    : []

  const handleUpdateTratamientoEstado = async (tratamientoId: number, estado: TratamientoEstado) => {
    const result = await updateTratamiento(tratamientoId, { 
      estado,
      fecha_fin: estado === 'completado' ? new Date().toISOString().split('T')[0] : undefined
    })
    if (result) {
      toast.success(`Tratamiento marcado como ${estado}`)
      if (selectedPaciente) {
        fetchTratamientos(selectedPaciente.id_paciente)
      }
    } else {
      toast.error('Error al actualizar tratamiento')
    }
  }

  const handlePrintExpediente = async () => {
    if (!selectedPaciente) return
    
    try {
      // Usar el nuevo componente de impresión mejorado con todos los campos NOM-024
      imprimirExpediente({
        paciente: selectedPaciente,
        tratamientos: pacienteTratamientos,
        evoluciones: evoluciones,
        podologos: podologos
      })
      
      toast.success('Expediente preparado para impresión')
    } catch (error: any) {
      console.error('Error al generar expediente:', error)
      toast.error(error.message || 'Error al generar expediente para impresión')
    }
  }

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Historial de Pacientes</h1>
            <p className="text-sm text-muted-foreground">Base de datos completa de pacientes y su historial clínico</p>
          </div>
          <Button onClick={handleCreatePaciente}>
            <Plus size={20} />
            Nuevo Paciente
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden p-6">
        <div className="grid grid-cols-3 gap-6 h-full">
          <div className="col-span-1 space-y-4">
            <div className="relative">
              <MagnifyingGlass size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por nombre, documento o teléfono..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            <Card className="h-[calc(100vh-240px)] overflow-hidden">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Pacientes ({filteredPacientes.length})</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-y-auto h-[calc(100%-60px)]">
                  {filteredPacientes.map((paciente) => (
                    <div
                      key={paciente.id_paciente}
                      onClick={() => handleViewPaciente(paciente)}
                      className="p-4 border-b border-border hover:bg-muted/50 cursor-pointer transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-semibold text-foreground">
                            {paciente.nombres} {paciente.apellidos}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {paciente.documento_id || 'Sin documento'}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {calculateAge(paciente.fecha_nacimiento)} años • {paciente.sexo}
                          </p>
                        </div>
                        {paciente.activo && (
                          <Badge variant="outline" className="text-xs">Activo</Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="col-span-2">
            {selectedPaciente ? (
              <Card className="h-full overflow-hidden">
                <CardHeader className="border-b border-border">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-xl">
                        {selectedPaciente.nombres} {selectedPaciente.apellidos}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        {calculateAge(selectedPaciente.fecha_nacimiento)} años • {selectedPaciente.sexo}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={handlePrintExpediente}>
                        <Printer size={16} className="mr-1" />
                        Imprimir
                      </Button>
                      <Button size="sm" onClick={() => handleEditPaciente(selectedPaciente)}>
                        Editar
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-6 overflow-y-auto h-[calc(100%-90px)]">
                  <Tabs defaultValue="datos">
                    <TabsList className="mb-4">
                      <TabsTrigger value="datos">Datos Personales</TabsTrigger>
                      <TabsTrigger value="tratamientos">Tratamientos</TabsTrigger>
                      <TabsTrigger value="citas">Citas</TabsTrigger>
                    </TabsList>

                    <TabsContent value="datos" className="space-y-6">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <User size={16} />
                            <span>Nombres</span>
                          </div>
                          <p className="text-foreground font-medium">{selectedPaciente.nombres}</p>
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <User size={16} />
                            <span>Apellidos</span>
                          </div>
                          <p className="text-foreground font-medium">{selectedPaciente.apellidos}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <CalendarBlank size={16} />
                            <span>Fecha de Nacimiento</span>
                          </div>
                          <p className="text-foreground font-medium">
                            {new Date(selectedPaciente.fecha_nacimiento).toLocaleDateString('es')}
                          </p>
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <IdentificationCard size={16} />
                            <span>Documento</span>
                          </div>
                          <p className="text-foreground font-medium">{selectedPaciente.documento_id || 'No registrado'}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Phone size={16} />
                            <span>Teléfono</span>
                          </div>
                          <p className="text-foreground font-medium">{selectedPaciente.telefono}</p>
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <EnvelopeSimple size={16} />
                            <span>Email</span>
                          </div>
                          <p className="text-foreground font-medium">{selectedPaciente.email || 'No registrado'}</p>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <MapPin size={16} />
                          <span>Domicilio</span>
                        </div>
                        <p className="text-foreground font-medium">{selectedPaciente.domicilio || 'No registrado'}</p>
                      </div>

                      {/* NOM-024 Fields Display - Collapsible */}
                      {(selectedPaciente.curp || selectedPaciente.estado_nacimiento || selectedPaciente.nacionalidad || 
                        selectedPaciente.estado_residencia) && (
                        <Accordion type="single" collapsible className="border-t pt-4 mt-4">
                          <AccordionItem value="nom024-display" className="border-none">
                            <AccordionTrigger className="py-2">
                              <span className="text-sm font-medium text-muted-foreground">Datos NOM-024</span>
                            </AccordionTrigger>
                            <AccordionContent className="space-y-3 pt-2">
                              {selectedPaciente.curp && (
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">CURP</p>
                                  <p className="text-sm font-mono font-medium">{selectedPaciente.curp}</p>
                                </div>
                              )}
                              
                              {selectedPaciente.estado_nacimiento && (
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">Estado de Nacimiento</p>
                                  <p className="text-sm font-medium">
                                    {ESTADOS_MEXICO.find(e => e.codigo === selectedPaciente.estado_nacimiento)?.nombre || selectedPaciente.estado_nacimiento}
                                  </p>
                                </div>
                              )}

                              {selectedPaciente.nacionalidad && (
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">Nacionalidad</p>
                                  <p className="text-sm font-medium">{selectedPaciente.nacionalidad}</p>
                                </div>
                              )}

                              {(selectedPaciente.estado_residencia || selectedPaciente.municipio_residencia || 
                                selectedPaciente.localidad_residencia) && (
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">Residencia</p>
                                  <p className="text-sm font-medium">
                                    {selectedPaciente.localidad_residencia && `${selectedPaciente.localidad_residencia}, `}
                                    {selectedPaciente.municipio_residencia && `${selectedPaciente.municipio_residencia}, `}
                                    {selectedPaciente.estado_residencia && (
                                      ESTADOS_MEXICO.find(e => e.codigo === selectedPaciente.estado_residencia)?.nombre || 
                                      selectedPaciente.estado_residencia
                                    )}
                                  </p>
                                </div>
                              )}
                            </AccordionContent>
                          </AccordionItem>
                        </Accordion>
                      )}
                    </TabsContent>

                    <TabsContent value="tratamientos" className="space-y-4">
                      <div className="flex justify-end mb-4">
                        <Button onClick={handleAddTratamiento} size="sm">
                          <Plus size={16} />
                          Nuevo Tratamiento
                        </Button>
                      </div>
                      {pacienteTratamientos.length > 0 ? (
                        pacienteTratamientos.map((tratamiento) => (
                          <Card key={tratamiento.id_tratamiento}>
                            <CardHeader>
                              <div className="flex items-center justify-between">
                                <CardTitle className="text-base">{tratamiento.problema}</CardTitle>
                                <div className="flex items-center gap-2">
                                  <Badge variant={tratamiento.estado === 'activo' ? 'default' : 'secondary'}>
                                    {tratamiento.estado}
                                  </Badge>
                                  {tratamiento.estado === 'activo' && (
                                    <Button 
                                      size="sm" 
                                      variant="outline"
                                      onClick={() => handleUpdateTratamientoEstado(tratamiento.id_tratamiento, 'completado')}
                                    >
                                      Completar
                                    </Button>
                                  )}
                                </div>
                              </div>
                              <p className="text-sm text-muted-foreground">
                                Inicio: {new Date(tratamiento.fecha_inicio).toLocaleDateString('es')}
                                {tratamiento.fecha_fin && ` • Fin: ${new Date(tratamiento.fecha_fin).toLocaleDateString('es')}`}
                              </p>
                            </CardHeader>
                            <CardContent>
                              {tratamiento.notas_adicionales && (
                                <p className="text-sm text-muted-foreground mb-4">{tratamiento.notas_adicionales}</p>
                              )}
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <p className="text-sm font-medium">
                                    Evoluciones ({tratamiento.evoluciones || [].length})
                                  </p>
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={() => handleAddEvolucion(tratamiento)}
                                  >
                                    <Plus size={16} />
                                    Agregar Evolución
                                  </Button>
                                </div>
                                {tratamiento.evoluciones || [].map((evolucion) => (
                                  <div key={evolucion.id_evolucion} className="p-3 bg-muted rounded-md">
                                    <div className="flex items-center justify-between mb-2">
                                      <p className="text-xs font-medium">
                                        {evolucion.podologo?.nombres} {evolucion.podologo?.apellidos}
                                      </p>
                                      <p className="text-xs text-muted-foreground">
                                        {new Date(evolucion.fecha_visita).toLocaleDateString('es')}
                                      </p>
                                    </div>
                                    {evolucion.tipo_visita && (
                                      <p className="text-xs text-muted-foreground mb-1">
                                        Tipo: {evolucion.tipo_visita}
                                      </p>
                                    )}
                                    <p className="text-sm text-foreground">{evolucion.nota}</p>
                                  </div>
                                ))}
                              </div>
                            </CardContent>
                          </Card>
                        ))
                      ) : (
                        <div className="text-center py-12">
                          <p className="text-muted-foreground">No hay tratamientos registrados</p>
                          <Button onClick={handleAddTratamiento} size="sm" className="mt-4">
                            <Plus size={16} />
                            Crear Primer Tratamiento
                          </Button>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="citas" className="space-y-4">
                      <div className="text-center text-muted-foreground py-8">
                        <CalendarBlank size={48} className="mx-auto mb-2 opacity-50" />
                        <p>Las citas del paciente se gestionan desde el módulo Agenda</p>
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            ) : (
              <div className="h-full flex items-center justify-center text-center">
                <div>
                  <User size={64} className="mx-auto text-muted-foreground mb-4" />
                  <p className="text-lg font-medium text-foreground">Seleccione un paciente</p>
                  <p className="text-sm text-muted-foreground">
                    Haga clic en un paciente de la lista para ver su historial completo
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog open={isCreateMode || isEditMode} onOpenChange={(open) => {
        if (!open) {
          setIsCreateMode(false)
          setIsEditMode(false)
          setSelectedPaciente(null)
        }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{isEditMode ? 'Editar Paciente' : 'Nuevo Paciente'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 max-h-[600px] overflow-y-auto px-1">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="nombres">Nombres *</Label>
                <Input
                  id="nombres"
                  value={formData.nombres}
                  onChange={(e) => setFormData({ ...formData, nombres: e.target.value })}
                  placeholder="Nombres del paciente"
                />
              </div>
              <div>
                <Label htmlFor="apellidos">Apellidos *</Label>
                <Input
                  id="apellidos"
                  value={formData.apellidos}
                  onChange={(e) => setFormData({ ...formData, apellidos: e.target.value })}
                  placeholder="Apellidos del paciente"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="fecha_nacimiento">Fecha de Nacimiento *</Label>
                <Input
                  id="fecha_nacimiento"
                  type="date"
                  value={formData.fecha_nacimiento}
                  onChange={(e) => setFormData({ ...formData, fecha_nacimiento: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="sexo">Sexo *</Label>
                <Select
                  value={formData.sexo}
                  onValueChange={(value) => setFormData({ ...formData, sexo: value })}
                >
                  <SelectTrigger id="sexo">
                    <SelectValue placeholder="Seleccionar" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Masculino">Masculino</SelectItem>
                    <SelectItem value="Femenino">Femenino</SelectItem>
                    <SelectItem value="Otro">Otro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="telefono">Teléfono *</Label>
                <Input
                  id="telefono"
                  value={formData.telefono}
                  onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                  placeholder="+52 123 456 7890"
                />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="correo@ejemplo.com"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="documento_id">Documento de Identidad</Label>
              <Input
                id="documento_id"
                value={formData.documento_id}
                onChange={(e) => setFormData({ ...formData, documento_id: e.target.value })}
                placeholder="INE, Pasaporte, etc."
              />
            </div>

            <div>
              <Label htmlFor="domicilio">Domicilio</Label>
              <Textarea
                id="domicilio"
                value={formData.domicilio}
                onChange={(e) => setFormData({ ...formData, domicilio: e.target.value })}
                placeholder="Calle, número, colonia, ciudad..."
                rows={3}
              />
            </div>

            {/* NOM-024 Optional Fields - Collapsible Section */}
            <Accordion type="single" collapsible className="border rounded-lg">
              <AccordionItem value="nom024">
                <AccordionTrigger className="px-4">
                  <span className="text-sm font-medium">Datos Adicionales NOM-024 (Opcional)</span>
                </AccordionTrigger>
                <AccordionContent className="px-4 space-y-4">
                  <p className="text-xs text-muted-foreground mb-3">
                    Campos opcionales para cumplimiento normativo. No son requeridos pero facilitan reportes oficiales.
                  </p>
                  
                  <div>
                    <Label htmlFor="curp">
                      CURP (Clave Única de Registro de Población)
                    </Label>
                    <Input
                      id="curp"
                      value={formData.curp}
                      onChange={(e) => setFormData({ ...formData, curp: e.target.value.toUpperCase() })}
                      placeholder="AAAA######HDFXXX##"
                      maxLength={18}
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      18 caracteres - Opcional
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="estado_nacimiento">Estado de Nacimiento</Label>
                      <Select
                        value={formData.estado_nacimiento}
                        onValueChange={(value) => setFormData({ ...formData, estado_nacimiento: value })}
                      >
                        <SelectTrigger id="estado_nacimiento">
                          <SelectValue placeholder="Seleccionar estado" />
                        </SelectTrigger>
                        <SelectContent>
                          {ESTADOS_MEXICO.map((estado) => (
                            <SelectItem key={estado.codigo} value={estado.codigo}>
                              {estado.nombre}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="nacionalidad">Nacionalidad</Label>
                      <Input
                        id="nacionalidad"
                        value={formData.nacionalidad}
                        onChange={(e) => setFormData({ ...formData, nacionalidad: e.target.value.toUpperCase() })}
                        placeholder="MEX"
                        maxLength={3}
                        className="font-mono"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Código ISO (3 letras)
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm font-semibold">Residencia Actual</Label>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="estado_residencia" className="text-xs">Estado</Label>
                        <Select
                          value={formData.estado_residencia}
                          onValueChange={(value) => setFormData({ ...formData, estado_residencia: value })}
                        >
                          <SelectTrigger id="estado_residencia">
                            <SelectValue placeholder="Seleccionar" />
                          </SelectTrigger>
                          <SelectContent>
                            {ESTADOS_MEXICO.map((estado) => (
                              <SelectItem key={estado.codigo} value={estado.codigo}>
                                {estado.nombre}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label htmlFor="municipio_residencia" className="text-xs">Municipio</Label>
                        <Input
                          id="municipio_residencia"
                          value={formData.municipio_residencia}
                          onChange={(e) => setFormData({ ...formData, municipio_residencia: e.target.value })}
                          placeholder="Nombre del municipio"
                        />
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="localidad_residencia" className="text-xs">Localidad</Label>
                      <Input
                        id="localidad_residencia"
                        value={formData.localidad_residencia}
                        onChange={(e) => setFormData({ ...formData, localidad_residencia: e.target.value })}
                        placeholder="Nombre de la localidad o colonia"
                      />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            <div className="flex gap-2 justify-end pt-4">
              <Button variant="outline" onClick={() => {
                setIsCreateMode(false)
                setIsEditMode(false)
              }}>
                Cancelar
              </Button>
              <Button onClick={handleSavePaciente}>
                {isEditMode ? 'Actualizar' : 'Crear'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showTratamientoModal} onOpenChange={setShowTratamientoModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Nuevo Tratamiento</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="problema">Problema / Diagnóstico *</Label>
              <Input
                id="problema"
                value={tratamientoForm.problema}
                onChange={(e) => setTratamientoForm({ ...tratamientoForm, problema: e.target.value })}
                placeholder="Ej: Fascitis plantar, Uña encarnada, etc."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="fecha_inicio">Fecha de Inicio *</Label>
                <Input
                  id="fecha_inicio"
                  type="date"
                  value={tratamientoForm.fecha_inicio}
                  onChange={(e) => setTratamientoForm({ ...tratamientoForm, fecha_inicio: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="fecha_fin">Fecha de Fin</Label>
                <Input
                  id="fecha_fin"
                  type="date"
                  value={tratamientoForm.fecha_fin}
                  onChange={(e) => setTratamientoForm({ ...tratamientoForm, fecha_fin: e.target.value })}
                />
              </div>
            </div>

            <div>
              <Label htmlFor="estado">Estado</Label>
              <Select
                value={tratamientoForm.estado}
                onValueChange={(value: TratamientoEstado) => setTratamientoForm({ ...tratamientoForm, estado: value })}
              >
                <SelectTrigger id="estado">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="activo">Activo</SelectItem>
                  <SelectItem value="completado">Completado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="notas_adicionales">Notas Adicionales</Label>
              <Textarea
                id="notas_adicionales"
                value={tratamientoForm.notas_adicionales}
                onChange={(e) => setTratamientoForm({ ...tratamientoForm, notas_adicionales: e.target.value })}
                placeholder="Observaciones, plan de tratamiento, indicaciones..."
                rows={4}
              />
            </div>

            <div className="flex gap-2 justify-end pt-4">
              <Button variant="outline" onClick={() => setShowTratamientoModal(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSaveTratamiento}>
                Crear Tratamiento
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showEvolucionModal} onOpenChange={setShowEvolucionModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Nueva Evolución</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="podologo_id">Podólogo *</Label>
              <Select
                value={evolucionForm.podologo_id.toString()}
                onValueChange={(value) => setEvolucionForm({ ...evolucionForm, podologo_id: parseInt(value) })}
              >
                <SelectTrigger id="podologo_id">
                  <SelectValue placeholder="Seleccionar podólogo" />
                </SelectTrigger>
                <SelectContent>
                  {podologos.map((podologo) => (
                    <SelectItem key={podologo.id_podologo} value={podologo.id_podologo.toString()}>
                      {podologo.nombres} {podologo.apellidos}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="fecha_visita">Fecha de Visita *</Label>
                <Input
                  id="fecha_visita"
                  type="date"
                  value={evolucionForm.fecha_visita}
                  onChange={(e) => setEvolucionForm({ ...evolucionForm, fecha_visita: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="tipo_visita">Tipo de Visita</Label>
                <Input
                  id="tipo_visita"
                  value={evolucionForm.tipo_visita}
                  onChange={(e) => setEvolucionForm({ ...evolucionForm, tipo_visita: e.target.value })}
                  placeholder="Ej: Seguimiento, Control, Evaluación"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="nota">Nota Clínica (SOAP) *</Label>
              <Textarea
                id="nota"
                value={evolucionForm.nota}
                onChange={(e) => setEvolucionForm({ ...evolucionForm, nota: e.target.value })}
                placeholder="S: Subjetivo - Lo que el paciente refiere&#10;O: Objetivo - Hallazgos del examen físico&#10;A: Análisis - Impresión diagnóstica&#10;P: Plan - Tratamiento y seguimiento"
                rows={8}
              />
            </div>

            <div>
              <Label htmlFor="signos_vitales">Signos Vitales (JSON opcional)</Label>
              <Textarea
                id="signos_vitales"
                value={typeof evolucionForm.signos_vitales === 'string' ? evolucionForm.signos_vitales : JSON.stringify(evolucionForm.signos_vitales || {})}
                onChange={(e) => setEvolucionForm({ ...evolucionForm, signos_vitales: e.target.value as any })}
                placeholder='{"presion": "120/80", "pulso": "72", "temperatura": "36.5"}'
                rows={3}
              />
            </div>

            {/* NOM-024 CIE-10 Fields - Collapsible Section */}
            <Accordion type="single" collapsible className="border rounded-lg">
              <AccordionItem value="nom024-codes">
                <AccordionTrigger className="px-4">
                  <span className="text-sm font-medium">Códigos de Diagnóstico NOM-024 (Opcional)</span>
                </AccordionTrigger>
                <AccordionContent className="px-4 space-y-4">
                  <p className="text-xs text-muted-foreground mb-3">
                    Códigos opcionales para reportes estadísticos y cumplimiento normativo. No son requeridos pero facilitan la trazabilidad.
                  </p>
                  
                  <div>
                    <Label htmlFor="diagnostico_codigo_cie10">
                      Código de Diagnóstico CIE-10
                    </Label>
                    <Input
                      id="diagnostico_codigo_cie10"
                      value={evolucionForm.diagnostico_codigo_cie10}
                      onChange={(e) => setEvolucionForm({ ...evolucionForm, diagnostico_codigo_cie10: e.target.value.toUpperCase() })}
                      placeholder="Ej: M21.6 - Hallux valgus"
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Clasificación Internacional de Enfermedades (CIE-10)
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="procedimiento_codigo">
                      Código de Procedimiento
                    </Label>
                    <Input
                      id="procedimiento_codigo"
                      value={evolucionForm.procedimiento_codigo}
                      onChange={(e) => setEvolucionForm({ ...evolucionForm, procedimiento_codigo: e.target.value.toUpperCase() })}
                      placeholder="Ej: QUIR-001 - Corrección de uña encarnada"
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Código del procedimiento realizado
                    </p>
                  </div>

                  <div className="bg-blue-50 p-3 rounded-lg text-xs text-blue-900">
                    <p className="font-medium mb-1">💡 Información</p>
                    <p>
                      Estos campos son opcionales pero útiles para generar reportes estadísticos y cumplir con normativas oficiales.
                      En el futuro podrán tener autocompletado con el catálogo oficial CIE-10.
                    </p>
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            <div className="flex gap-2 justify-end pt-4">
              <Button variant="outline" onClick={() => {
                setShowEvolucionModal(false)
                setSelectedTratamiento(null)
              }}>
                Cancelar
              </Button>
              <Button onClick={handleSaveEvolucion}>
                Guardar Evolución
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

