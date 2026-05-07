// 1. 用户服务：
// 1.1. use_api：对外提供API服务的
// 1.2. user_service：用GRPC实现，对内提供服务的
// 单独部署在一个域名下
// 单点登录

// 2. 秒杀服务
// 2.1. seckill_api：对外提供秒杀API接口服务的
// 单独部署在一个域名下

// 3. 管理系统
// 3.1. Django+Vue
// 单独部署在一个域名下
import useUserStore from "../../plugins/stores";


class BaseUserHttp{
	constructor(){
		this.base_url = "http://192.168.0.13:8000"
	}
	
	_build_fulll_url(path){
		return this.base_url + path
	}
		
	_request1(path, data, method){
		const url = this._build_fulll_url(path);
		const authStore = useUserStore();
		return new Promise((resolve, reject) => {
			uni.request({
				url: url,
				method: method,
				data: data,
				header: {
					Authorization: "Bearer " + authStore.access_token
				},
				success: async (response) => {
					// 后端返回的参数response.data
					console.log(response);
					resolve(response.data);
				},
				fail: (error) => {
					reject(error);
				}
			})
		})
	}
	
	async update_access_token(){
		const url = this._build_fulll_url('/user/refresh/token')
		const authStore = useUserStore()
		if(!authStore.is_logined){
			uni.showToast({
				title: "请先登录！"
			})
			throw new Error("请先登录！")
		}
		const response = await uni.request({
			url: url,
			method: 'GET',
			header:{
				Authorization: "Bearer " + authStore.refresh_token
			}
		})
		if(response.statusCode == 200){
			let access_token = response.data.access_token;
			authStore.setAccessToken(access_token);
		}
		// 401错误：refresh token过期
		else if(response.statusCode == 401){
			uni.switchTab({
				url: "/pages/index/index"
			})
			throw new Error('登录过期，请重新登录！')
		}
	}
	
	async _request(path, data, method){
		const url = this._build_fulll_url(path);
		const authStore = useUserStore();
		const response = await uni.request({
			url: url,
			method: method,
			data: data,
			header: {
				Authorization: "Bearer " + authStore.access_token
			}
		})
		if(response.statusCode == 200){
			return response.data;
		}
		// 如果是403：代表access token过期了
		else if(response.statusCode == 403){
			// 重新获取access_token
			console.log('access token过期了，准备重新获取access token！');
			console.log('重新获取access token前！');
			await this.update_access_token()
			console.log('重新获取access token后！');
			return this._request(path, data, method)
		}else{
			uni.showToast({
				title: response.data.detail
			})
		}
	}
	
	get(path, params){
		return this._request(path, params, 'GET')
	}
	
	post(path, data){
		return this._request(path, data, 'POST')
	}
	
	put(path, data){
		return this._request(path, data, 'PUT')
	}
	
	delete(path, data){
		return this._request(path, data, 'DELETE')
	}
}

export default new BaseUserHttp();