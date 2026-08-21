import { useState } from 'react'
import { useCredentials, useSaveCredential, useDeleteCredential } from '@/hooks/useApi'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input, Label } from '@/components/ui/Input'
import { KeyRound, ShieldCheck, AlertTriangle, Trash2, Save } from 'lucide-react'
import { toast } from 'sonner'

const SITE_CARDS: Array<{ site: string; name: string; blurb: string }> = [
  {
    site: 'jobbank',
    name: 'JobBank Canada',
    blurb: 'Login required — the bot signs in before filling applications.',
  },
  {
    site: 'greenhouse',
    name: 'Greenhouse boards',
    blurb: 'Public boards rarely need a login; saved anyway if one appears.',
  },
  {
    site: 'lever',
    name: 'Lever postings',
    blurb: 'Public postings; no login needed in the usual flow.',
  },
]

/**
 * Job-site logins. This form talks to /settings/credentials directly (not
 * through the generic settings PATCH) because passwords must never ride
 * along with AppSettings or be echoed back by any response.
 */
export function CredentialsSettingsForm() {
  const { data: creds, isLoading } = useCredentials()
  const saveMutation = useSaveCredential()
  const deleteMutation = useDeleteCredential()

  // Local draft per site: username + password (password starts blank and is
  // only sent when typed — an empty password keeps the stored one).
  const [drafts, setDrafts] = useState<Record<string, { username: string; password: string }>>({})

  const encryptionConfigured = creds?.encryption_configured ?? false
  const siteMap = new Map((creds?.sites || []).map((s) => [s.site, s]))

  const getDraft = (site: string) => drafts[site] || { username: '', password: '' }

  const setDraft = (site: string, patch: Partial<{ username: string; password: string }>) => {
    setDrafts((prev) => ({ ...prev, [site]: { ...getDraft(site), ...patch } }))
  }

  const handleSave = async (site: string) => {
    const draft = getDraft(site)
    if (!draft.username.trim() && !draft.password) {
      toast.error('Enter a username (and optionally a password)')
      return
    }
    try {
      await saveMutation.mutateAsync({
        site,
        username: draft.username.trim(),
        password: draft.password || undefined,
      })
      toast.success(`${site} login saved — encrypted at rest`)
      setDraft(site, { password: '' })
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || `Could not save ${site} login`)
    }
  }

  const handleDelete = async (site: string) => {
    if (!window.confirm(`Remove the stored ${site} login? The bot will stop at its login page instead.`)) return
    try {
      await deleteMutation.mutateAsync(site)
      toast.success(`${site} login removed`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || `Could not remove ${site} login`)
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">
          Loading saved logins…
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {!encryptionConfigured && (
        <div className="rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5" />
          <div className="text-sm text-amber-900 dark:text-amber-200">
            <p className="font-medium">Encryption key not configured on the server</p>
            <p className="mt-1">
              Set <code className="px-1 rounded bg-amber-100 dark:bg-amber-900/40">CREDENTIAL_ENCRYPTION_KEY</code> in the
              backend environment first. Logins cannot be saved until then.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {SITE_CARDS.map(({ site, name, blurb }) => {
          const existing = siteMap.get(site)
          const draft = getDraft(site)
          const configured = !!existing?.configured
          return (
            <Card key={site} variant="outline" className="flex flex-col">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <KeyRound className="w-4 h-4" /> {name}
                  </CardTitle>
                  <Badge variant={configured ? 'success' : 'neutral'} className="text-xs">
                    {configured ? 'Saved' : 'Not set'}
                  </Badge>
                </div>
                <CardDescription>{blurb}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 pt-0 flex-1 flex flex-col">
                {configured && existing?.username_hint && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Stored for <span className="font-mono">{existing.username_hint}</span>
                  </p>
                )}
                <div className="space-y-1.5">
                  <Label htmlFor={`${site}-username`}>Username / email</Label>
                  <Input
                    id={`${site}-username`}
                    value={draft.username || existing?.username_hint || ''}
                    onChange={(e) => setDraft(site, { username: e.target.value })}
                    placeholder={configured ? '(keep current)' : 'you@example.com'}
                    autoComplete="off"
                    disabled={!encryptionConfigured}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor={`${site}-password`}>Password</Label>
                  <Input
                    id={`${site}-password`}
                    type="password"
                    value={draft.password}
                    onChange={(e) => setDraft(site, { password: e.target.value })}
                    placeholder={configured ? '•••••••• (unchanged if blank)' : 'Password'}
                    autoComplete="new-password"
                    disabled={!encryptionConfigured}
                  />
                </div>
                <div className="flex items-center justify-between pt-2 mt-auto">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(site)}
                    disabled={!configured || deleteMutation.isPending}
                    loading={deleteMutation.isPending}
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1" /> Remove
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleSave(site)}
                    loading={saveMutation.isPending}
                    disabled={!encryptionConfigured}
                  >
                    <Save className="w-3.5 h-3.5 mr-1" /> Save
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <p className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5" />
        Passwords are encrypted before storage, never logged, and never returned to the browser — only a masked hint like
        va***@gmail.com comes back.
      </p>
    </div>
  )
}
