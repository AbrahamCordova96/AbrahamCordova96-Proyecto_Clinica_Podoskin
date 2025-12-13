// Vista de Auditoría conectada al backend
import { useState, useEffect } from 'react'
import { AuditView } from '@/components/AuditView'
import { auditService } from '@/services/auditService'
import { toast } from 'sonner'
import { useAuthStore } from '@/modules/auth/stores/authStore'

export function AuditPage() {
  const { user } = useAuthStore()
  const [auditLogs, setAuditLogs] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true)
        // Obtener logs de auditoría
        const logs = await auditService.getAll()
        setAuditLogs(logs)

        // Extraer usuarios únicos de los logs
        const uniqueUsers = Array.from(
          new Map(
            logs
              .filter((log: any) => log.usuario)
              .map((log: any) => [log.usuario_id, log.usuario])
          ).values()
        )
        setUsuarios(uniqueUsers as any)
      } catch (error: any) {
        console.error('Error al cargar auditoría:', error)
        if (error.response?.status === 403) {
          toast.error('No tienes permisos para ver la auditoría')
        } else if (error.response?.status === 404) {
          toast.warning('El endpoint de auditoría aún no está disponible')
          // Usar datos vacíos para desarrollo
          setAuditLogs([])
          setUsuarios([])
        } else {
          toast.error('Error al cargar los logs de auditoría')
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Cargando auditoría...</p>
        </div>
      </div>
    )
  }

  return <AuditView auditLogs={auditLogs} usuarios={usuarios} />
}
