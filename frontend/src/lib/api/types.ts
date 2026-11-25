/**
 * Friendly names for the generated API types.
 * types.gen.ts is generated from the backend (`npm run gen:api`); never edit it by hand.
 */
import type { components } from './types.gen'

type Schemas = components['schemas']

export type ResumeSummary = Schemas['ResumeSummary']
export type ResumeDetail = Schemas['ResumeDetail']
export type ResumeProfile = Schemas['ResumeProfile']
export type Entry = Schemas['Entry']
export type Check = Schemas['Check']
export type JdSummary = Schemas['JdSummary']
export type JdDetail = Schemas['JdDetail']
export type AnalysisSummary = Schemas['AnalysisSummary']
export type AnalysisDetail = Schemas['AnalysisDetail']
export type CreateAnalysis = Schemas['CreateAnalysis']
export type GeneralReview = Schemas['GeneralReview']
export type JdMatch = Schemas['JdMatch']
export type SubScore = Schemas['SubScore']
export type BulletFeedback = Schemas['BulletFeedback']
export type RequirementMatch = Schemas['RequirementMatch']
export type KnockoutResult = Schemas['KnockoutResult']
export type TailoredBullet = Schemas['TailoredBullet']

// Mock interviews (v2)
export type CreateInterview = Schemas['CreateInterview']
export type InterviewSummary = Schemas['InterviewSummary']
export type InterviewDetail = Schemas['InterviewDetail']
export type InterviewReport = Schemas['InterviewReport']
export type QuestionReport = Schemas['QuestionReport']
export type TurnOut = Schemas['TurnOut']
export type TurnEvaluation = Schemas['TurnEvaluation']
export type AnswerRequest = Schemas['AnswerRequest']
export type InterviewOverview = Schemas['InterviewOverview']

// Planner (v2)
export type PlannerProfile = Schemas['PlannerProfile']
export type ProfileResponse = Schemas['ProfileResponse']
export type ProfileSuggestions = Schemas['ProfileSuggestions']
export type PlanPreview = Schemas['PlanPreview']
export type PlanDetail = Schemas['PlanDetail']
export type PlanTask = Schemas['TaskOut']
export type SubjectAllocation = Schemas['SubjectAllocation']
export type WeekMilestone = Schemas['WeekMilestone']
export type Feasibility = Schemas['Feasibility']
export type CheckinRequest = Schemas['CheckinRequest']
export type PlannerOverview = Schemas['PlannerOverview']

// Dashboard + coach (v2)
export type DashboardOverview = Schemas['DashboardOverview']
export type ReadinessPart = Schemas['ReadinessPart']
export type CoachMessage = Schemas['CoachMessage']
export type CoachAction = Schemas['CoachAction']
