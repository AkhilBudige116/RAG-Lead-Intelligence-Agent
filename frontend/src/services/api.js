import axios from 'axios';

const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getStats = async () => {
  const res = await api.get('/api/stats');
  return res.data;
};

export const getLeads = async (params = {}) => {
  const res = await api.get('/api/leads', { params });
  return res.data;
};

export const getLead = async (id) => {
  const res = await api.get(`/api/leads/${id}`);
  return res.data;
};

export const updateLeadSector = async (id, data) => {
  const res = await api.patch(`/api/leads/${id}/sector`, data);
  return res.data;
};

export const uploadFiles = async (formData, onProgress) => {
  const res = await api.post('/api/uploads', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
  return res.data;
};

export const ingestEmailJson = async (payload) => {
  const res = await api.post('/api/emails/ingest', payload);
  return res.data;
};

export const getBatches = async (params = {}) => {
  const res = await api.get('/api/batches', { params });
  return res.data;
};

export const getBatch = async (id) => {
  const res = await api.get(`/api/batches/${id}`);
  return res.data;
};

export const getSectors = async (includeInactive = false) => {
  const res = await api.get('/api/sectors', { params: { include_inactive: includeInactive } });
  return res.data;
};

export const createSector = async (data) => {
  const res = await api.post('/api/sectors', data);
  return res.data;
};

export const updateSector = async (id, data) => {
  const res = await api.patch(`/api/sectors/${id}`, data);
  return res.data;
};

export const deactivateSector = async (id) => {
  const res = await api.delete(`/api/sectors/${id}`);
  return res.data;
};

export const reindexSector = async (id) => {
  const res = await api.post(`/api/sectors/${id}/reindex`);
  return res.data;
};

export const reindexAllSectors = async () => {
  const res = await api.post('/api/sectors/reindex-all');
  return res.data;
};

export const getReviewQueue = async (params = {}) => {
  const res = await api.get('/api/review/queue', { params });
  return res.data;
};

export const processReviewAction = async (id, data) => {
  const res = await api.post(`/api/review/${id}/action`, data);
  return res.data;
};

export const getDuplicates = async () => {
  const res = await api.get('/api/duplicates');
  return res.data;
};

export const confirmMerge = async (keptCompanyId, mergedCompanyId) => {
  const res = await api.post('/api/duplicates/merge', {
    kept_company_id: keptCompanyId,
    merged_company_id: mergedCompanyId,
  });
  return res.data;
};

export const rejectDuplicate = async (duplicateLogId) => {
  const res = await api.post('/api/duplicates/reject', {
    duplicate_log_id: duplicateLogId,
  });
  return res.data;
};

export const undoMerge = async (duplicateLogId) => {
  const res = await api.post('/api/duplicates/undo', {
    duplicate_log_id: duplicateLogId,
  });
  return res.data;
};

export const getExportUrl = (format = 'csv', filters = {}) => {
  const params = new URLSearchParams({ format, ...filters });
  return `/api/export?${params.toString()}`;
};

export default api;
