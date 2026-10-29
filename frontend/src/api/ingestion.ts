import { apiClient } from './client'
import {
  CSVPreviewResponse,
  CSVImportResult,
  ImportJobItem,
  SMSParseResult,
} from '@/types'

export async function previewCsvStatementApi(
  accountId: string,
  file: File
): Promise<CSVPreviewResponse> {
  const formData = new FormData()
  formData.append('account_id', accountId)
  formData.append('file', file)

  return apiClient<CSVPreviewResponse>('/ingestion/csv-preview', {
    method: 'POST',
    body: formData,
  })
}

export async function importCsvStatementApi(
  accountId: string,
  columnMapping: Record<string, string | null>,
  bankFormat: string,
  file: File
): Promise<CSVImportResult> {
  const formData = new FormData()
  formData.append('account_id', accountId)
  formData.append('column_mapping', JSON.stringify(columnMapping))
  formData.append('bank_format', bankFormat)
  formData.append('file', file)

  return apiClient<CSVImportResult>('/ingestion/csv-import', {
    method: 'POST',
    body: formData,
  })
}

export async function listImportJobsApi(): Promise<ImportJobItem[]> {
  return apiClient<ImportJobItem[]>('/ingestion/jobs')
}

export function getJobErrorsDownloadUrl(jobId: string): string {
  return `/api/v1/ingestion/jobs/${jobId}/errors.csv`
}

export async function parseSmsApi(smsText: string): Promise<SMSParseResult> {
  return apiClient<SMSParseResult>('/ingestion/parse-sms', {
    method: 'POST',
    body: JSON.stringify({ sms_text: smsText }),
  })
}

export async function importSmsTransactionApi(data: {
  account_id: string
  category_id: string
  amount_inr: number
  transaction_type: string
  date: string
  narration: string
  merchant_name?: string
  payment_mode?: string
  reference_id?: string
}): Promise<{ status: string; transaction_id: string; message: string }> {
  return apiClient<{ status: string; transaction_id: string; message: string }>(
    '/ingestion/import-sms-transaction',
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )
}
