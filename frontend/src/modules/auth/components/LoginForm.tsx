import { useState } from 'react';
import { useAuthStore } from '../stores/authStore';
import { Warning, CircleNotch } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import LogoImage from '@/assets/images/Logo.png';

export const LoginForm = () => {
  const { login, isLoading, error, clearError } = useAuthStore();
  
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    
    try {
      await login(identifier, password);
    } catch (err) {
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 via-background to-accent/5 px-4">
      <div className="w-full max-w-md">
        <div className="bg-card rounded-2xl shadow-2xl border border-border p-8">
          
          <div className="text-center mb-8">
            <div className="mx-auto mb-6 flex items-center justify-center">
              <img src={LogoImage} alt="PodoSkin Logo" className="h-24 w-auto" />
            </div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Bienvenido a PodoSkin
            </h1>
            <p className="text-muted-foreground">
              Sistema de Gestión Clínica Podológica
            </p>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            
            <div className="space-y-2">
              <Label htmlFor="identifier" className="text-sm font-medium">
                Usuario, Email o ID
              </Label>
              <Input
                id="identifier"
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                className="w-full"
                placeholder="Ingresa tu usuario, email o ID"
                required
                disabled={isLoading}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Puedes usar tu usuario, email o ID estructurado (ej: ASGO-1213-00001)
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium">
                Contraseña
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full"
                placeholder="Ingresa tu contraseña"
                required
                disabled={isLoading}
              />
            </div>
            
            {error && (
              <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-4 flex items-start gap-3">
                <Warning className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" weight="fill" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-destructive">
                    Error de autenticación
                  </p>
                  <p className="text-sm text-destructive/80 mt-1">
                    {error}
                  </p>
                </div>
              </div>
            )}
            
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <CircleNotch className="w-5 h-5 animate-spin" />
                  <span>Iniciando sesión...</span>
                </span>
              ) : (
                <span>Iniciar Sesión</span>
              )}
            </Button>
          </form>
          
          <div className="mt-6 text-center">
            <a href="#" className="text-sm text-primary hover:underline">
              ¿Olvidaste tu contraseña?
            </a>
          </div>
        </div>
        
        {import.meta.env.DEV && (
          <div className="mt-6 bg-muted/50 rounded-lg p-4 text-xs text-muted-foreground border border-border">
            <p className="font-semibold mb-2 text-foreground">👤 Usuarios de prueba:</p>
            <div className="space-y-1 font-mono">
              <p>• Admin: <code className="bg-background px-2 py-1 rounded text-foreground">admin_santiago</code> / <code className="bg-background px-2 py-1 rounded text-foreground">Ornelas2025!</code></p>
              <p>• ID Admin: <code className="bg-background px-2 py-1 rounded text-foreground">ASGO-1213-00001</code></p>
              <p>• Podólogo: <code className="bg-background px-2 py-1 rounded text-foreground">dr.ornelas</code> / <code className="bg-background px-2 py-1 rounded text-foreground">Podo2024!</code></p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
