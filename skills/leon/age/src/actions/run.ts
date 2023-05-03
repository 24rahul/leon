import { leon } from '@sdk/leon'
import { IntermediateAnswer, FinalAnswer } from '@sdk/answer'

export async function run(): Promise<void> {
  await leon.answer(new IntermediateAnswer('intermediate answer'))

  await leon.answer(new FinalAnswer('final answer'))
}
