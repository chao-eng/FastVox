import axios from 'axios';

const client = axios.create({
  baseURL: '/api', // 这里的 /api 会被 Vite Proxy 转发到 :8000/api/v1
  timeout: 10000,
});

// 请求拦截器: 自动附带 JWT Token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('fastvox_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

// 响应拦截器: 处理处理登录超时
client.interceptors.response.use((response) => response.data, (error) => {
  if (error.response?.status === 401) {
    localStorage.removeItem('fastvox_token');
    window.location.href = '/login';
  }
  return Promise.reject(error);
});

export default client;
