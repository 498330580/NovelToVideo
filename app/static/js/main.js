// 全局配置
const config = {
    apiBaseUrl: '/',
    animationDuration: 300,
    autoHideToastr: 5000
};

// 提示库 - Toastr 包装
 const notify = {
    success: (message, title = '成功') => {
        toastr.success(message, title, {
            timeOut: 4000,
            progressBar: true
        });
    },
    error: (message, title = '错误') => {
        toastr.error(message, title, {
            timeOut: 5000,
            progressBar: true
        });
    },
    warning: (message, title = '警告') => {
        toastr.warning(message, title, {
            timeOut: 4000,
            progressBar: true
        });
    },
    info: (message, title = '提示') => {
        toastr.info(message, title, {
            timeOut: 4000,
            progressBar: true
        });
    }
};

// 工具函数
const utils = {
    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    },
    
    // 格式化时间段
    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}小时${minutes}分钟${secs}秒`;
        } else if (minutes > 0) {
            return `${minutes}分钟${secs}秒`;
        } else {
            return `${secs}秒`;
        }
    },
    
    // 会议于日时
    formatDate(date) {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    },
    
    // 会议于年月日 时间
    formatDateTime(date) {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    // 混合 class 名称
    classNames(...classes) {
        return classes.filter(Boolean).join(' ');
    },
    
    // 混合对象
    merge(target, source) {
        return Object.assign({}, target, source);
    },
    
    // 程冶上树 API 调用
    async fetchJSON(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('调用 API 错误:', error);
            throw error;
        }
    },
    
    // 验证邮箱
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },
    
    // 混合参数
    buildQueryString(params) {
        const searchParams = new URLSearchParams();
        for (const key in params) {
            if (params[key] !== null && params[key] !== undefined) {
                searchParams.append(key, params[key]);
            }
        }
        return searchParams.toString();
    },
    
    // 混合 URL
    buildURL(baseURL, params) {
        const queryString = this.buildQueryString(params);
        if (queryString) {
            return `${baseURL}?${queryString}`;
        }
        return baseURL;
    },
    
    // 测试库载入
    isLibraryLoaded(libName) {
        switch(libName.toLowerCase()) {
            case 'jquery':
                return typeof $ !== 'undefined';
            case 'toastr':
                return typeof toastr !== 'undefined';
            case 'aos':
                return typeof AOS !== 'undefined';
            case 'bootstrap':
                return typeof bootstrap !== 'undefined';
            default:
                return false;
        }
    },
    
    // 扰动减少的函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // 临时加载提示
    showLoading(message = '正在加载...') {
        if (notify && notify.info) {
            notify.info(message, '加载中');
        }
    },
    
    // 隐藏加载提示
    hideLoading() {
        // Toastr 会自动消失
    },
    
    // 显示错误信息
    showError(message) {
        notify.error(message);
    },
    
    // 显示成功信息
    showSuccess(message) {
        notify.success(message);
    }
};

// 方便的 API 类
 class API {
    static async get(endpoint, params = {}) {
        const url = utils.buildURL(endpoint, params);
        return utils.fetchJSON(url);
    }
    
    static async post(endpoint, data = {}) {
        return utils.fetchJSON(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    static async put(endpoint, data = {}) {
        return utils.fetchJSON(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    static async delete(endpoint) {
        return utils.fetchJSON(endpoint, {
            method: 'DELETE'
        });
    }
}

// 页面加载完成后执行
 document.addEventListener('DOMContentLoaded', function() {
    // 检查库是否加载
    console.log('Bootstrap 加载：', utils.isLibraryLoaded('bootstrap'));
    console.log('Toastr 加载：', utils.isLibraryLoaded('toastr'));
    console.log('AOS 加载：', utils.isLibraryLoaded('aos'));
    console.log('jQuery 加载：', utils.isLibraryLoaded('jquery'));
    
    // 初始化事件侦听器
    initializeEventListeners();
});

// 初始化事件侦听器
 function initializeEventListeners() {
    // 日准按鑲
    const buttons = document.querySelectorAll('[data-action]');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const action = this.dataset.action;
            // 执行对应的操作
            console.log('执行操作:', action);
        });
    });
}

// 导出全局对象
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { utils, notify, config, API };
}
