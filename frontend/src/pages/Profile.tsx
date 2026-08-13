import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { ResumeUpload } from '@/components/profile/ResumeUpload'
import { PersonalInfoForm } from '@/components/profile/PersonalInfoForm'
import { SkillsForm } from '@/components/profile/SkillsForm'
import { ExperienceForm } from '@/components/profile/ExperienceForm'
import { EducationForm } from '@/components/profile/EducationForm'
import { CertificationsForm } from '@/components/profile/CertificationsForm'
import { AdditionalExperienceForm } from '@/components/profile/AdditionalExperienceForm'
import { Upload, User, Sparkles, Briefcase, GraduationCap, Award, Star, CheckCircle } from 'lucide-react'
import { useProfileStore } from '@/store/index'
import { useJobSearchStore } from '@/store/index'
import { updateProfile, generateJobFilters } from '@/services/api'
import { CandidateProfile } from '@/types'
import { toast } from 'sonner'

const TABS = [
  { id: 'resume', label: 'Upload Resume', icon: Upload, description: 'Upload and parse your resume' },
  { id: 'personal', label: 'Personal Info', icon: User, description: 'Contact details and summary' },
  { id: 'skills', label: 'Skills', icon: Sparkles, description: 'Technical and soft skills' },
  { id: 'experience', label: 'Experience', icon: Briefcase, description: 'Work history and achievements' },
  { id: 'education', label: 'Education', icon: GraduationCap, description: 'Academic background' },
  { id: 'certifications', label: 'Certifications', icon: Award, description: 'Professional credentials' },
  { id: 'additional', label: 'Additional', icon: Star, description: 'Projects, publications, awards' },
] as const

type TabId = (typeof TABS)[number]['id']

export function Profile() {
  const navigate = useNavigate()
  const { profile, setProfile, resumeUploading } = useProfileStore()
  const { setFilters } = useJobSearchStore()
  const [activeTab, setActiveTab] = useState<TabId>('resume')
  const [savingTabs, setSavingTabs] = useState<Record<TabId, boolean>>({
    resume: false,
    personal: false,
    skills: false,
    experience: false,
    education: false,
    certifications: false,
    additional: false,
  })

  const handleSaveProfile = useCallback(
    async (updates: Partial<CandidateProfile>) => {
      if (!profile) return

      try {
        // Send the FULL profile merged with the current update so the backend
        // persists everything on the first save — not just the one tab being
        // saved.  Without this, saving a single tab overwrites the in-memory
        // profile with a backend response that has empty arrays for every
        // other section, losing the parsed resume data.
        const fullPayload = { ...profile, ...updates }
        const updated = await updateProfile(fullPayload)
        setProfile(updated)

        // Check if ALL tabs are now complete — if so, auto-generate job filters
        // and navigate to the job search page.
        const allTabs: TabId[] = ['personal', 'skills', 'experience', 'education', 'certifications', 'additional']
        const allComplete = allTabs.every((tabId) => {
          switch (tabId) {
            case 'personal':
              return !!updated.personal_info?.full_name && !!updated.personal_info?.email
            case 'skills':
              return (updated.skills?.length || 0) > 0
            case 'experience':
              return (updated.experience?.length || 0) > 0
            case 'education':
              return (updated.education?.length || 0) > 0
            case 'certifications':
              return (updated.certifications?.length || 0) > 0
            case 'additional':
              return (updated.additional_experience?.length || 0) > 0
            default:
              return false
          }
        })

        toast.success('Profile updated successfully')

        if (allComplete) {
          try {
            const result = await generateJobFilters()
            const filters = result.filters
            if (filters) {
              setFilters({
                keywords: filters.keywords,
                locations: filters.locations,
                job_types: filters.job_types as any,
                experience_levels: filters.experience_levels as any,
                sources: filters.sources as any,
                remote_only: filters.remote_only,
                posted_within_days: filters.posted_within_days,
              })
              toast.success('Job search filters generated! Navigating to job search...')
              navigate('/job-search')
            }
          } catch (filterErr: any) {
            console.error('Failed to generate job filters:', filterErr)
            toast.error('Profile saved. Could not auto-generate filters.')
          }
        }
      } catch (error: any) {
        console.error('Failed to update profile:', error)
        console.error('Server response:', JSON.stringify(error.response?.data, null, 2))
        console.error('Status:', error.response?.status)
        const serverMsg = error.response?.data?.detail
        if (serverMsg) {
          toast.error(`Server: ${serverMsg}`)
        } else {
          toast.error(`Failed to update profile (${error.response?.status || 'network error'})`)
        }
      }
    },
    [profile, setProfile, setFilters, navigate]
  )

  const handleResumeComplete = useCallback(
    (parsedProfile: any) => {
      setProfile(parsedProfile)
      setActiveTab('personal')
    },
    [setProfile]
  )

  const isTabComplete = (tabId: TabId) => {
    if (!profile) return false
    switch (tabId) {
      case 'personal':
        return !!profile.personal_info?.full_name && !!profile.personal_info?.email
      case 'skills':
        return (profile.skills?.length || 0) > 0
      case 'experience':
        return (profile.experience?.length || 0) > 0
      case 'education':
        return (profile.education?.length || 0) > 0
      case 'certifications':
        return (profile.certifications?.length || 0) > 0
      case 'additional':
        return (profile.additional_experience?.length || 0) > 0
      default:
        return false
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Profile</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage your candidate profile and resume
          </p>
        </div>
        {profile && (
          <div className="flex items-center gap-3">
            <Badge variant="success" className="text-sm">
              <CheckCircle className="w-3 h-3 mr-1" />
              Profile Complete
            </Badge>
          </div>
        )}
      </div>

      {/* Progress Indicator */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {TABS.map((tab, index) => (
              <div key={tab.id} className="flex items-center gap-2 min-w-0">
                <div
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
                    activeTab === tab.id
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                      : isTabComplete(tab.id as TabId)
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  <span className="text-sm font-medium hidden sm:inline">{tab.label}</span>
                </div>
                {index < TABS.length - 1 && (
                  <div
                    className={`w-8 h-0.5 rounded ${isTabComplete(tab.id as TabId) ? 'bg-green-400' : 'bg-slate-200 dark:bg-slate-700'}`}
                  />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Tab Content */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as TabId)} className="space-y-4">
        <TabsList className="grid w-full grid-cols-7">
          {TABS.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className="flex flex-col items-center gap-1 py-3 px-2 text-xs"
            >
              <tab.icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        {TABS.map((tab) => (
          <TabsContent key={tab.id} value={tab.id} className="space-y-4">
            <div className="text-sm text-slate-500 dark:text-slate-400">{tab.description}</div>

            {tab.id === 'resume' && (
              <ResumeUpload onComplete={handleResumeComplete} />
            )}

            {tab.id === 'personal' && (
              <PersonalInfoForm
                onSave={async (data) => {
                  setSavingTabs((prev) => ({ ...prev, personal: true }))
                  await handleSaveProfile({ personal_info: data })
                  setSavingTabs((prev) => ({ ...prev, personal: false }))
                }}
                isLoading={savingTabs.personal || resumeUploading}
              />
            )}

            {tab.id === 'skills' && (
              <SkillsForm
                onSave={async (data) => {
                  setSavingTabs((prev) => ({ ...prev, skills: true }))
                  await handleSaveProfile({ skills: data })
                  setSavingTabs((prev) => ({ ...prev, skills: false }))
                }}
                isLoading={savingTabs.skills}
              />
            )}

            {tab.id === 'experience' && (
              <ExperienceForm
                onSave={async (data) => {
                  setSavingTabs((prev) => ({ ...prev, experience: true }))
                  await handleSaveProfile({ experience: data })
                  setSavingTabs((prev) => ({ ...prev, experience: false }))
                }}
                isLoading={savingTabs.experience}
              />
            )}

            {tab.id === 'education' && (
              <EducationForm
                onSave={async (data) => {
                  setSavingTabs((prev) => ({ ...prev, education: true }))
                  await handleSaveProfile({ education: data })
                  setSavingTabs((prev) => ({ ...prev, education: false }))
                }}
                isLoading={savingTabs.education}
              />
            )}

            {tab.id === 'certifications' && (
              <CertificationsForm
                onSave={async (data) => {
                  setSavingTabs((prev) => ({ ...prev, certifications: true }))
                  await handleSaveProfile({ certifications: data })
                  setSavingTabs((prev) => ({ ...prev, certifications: false }))
                }}
                isLoading={savingTabs.certifications}
              />
            )}

            {tab.id === 'additional' && (
              <AdditionalExperienceForm
                onSave={async (data) => {
                  setSavingTabs((prev) => ({ ...prev, additional: true }))
                  await handleSaveProfile({ additional_experience: data })
                  setSavingTabs((prev) => ({ ...prev, additional: false }))
                }}
                isLoading={savingTabs.additional}
              />
            )}

            {!profile && tab.id !== 'resume' && (
              <Card className="border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
                <CardContent className="py-8 text-center">
                  <p className="text-amber-700 dark:text-amber-300">
                    Please upload your resume first to create your profile, or fill in your personal information to get started.
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}