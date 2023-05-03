import type { AnswerObject } from '@bridge/types'

export type ActionResponse = AnswerObject | null

export interface Versions {
  core: string
  'nodejs-bridge': string
}
