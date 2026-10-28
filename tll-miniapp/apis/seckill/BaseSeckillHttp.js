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
import userHttp from "../user/userHttp";


class BaseSeckillHttp{
	constructor(){
		this.base_url = "http://192.168.0.13:8100"
	}
	
	_build_fulll_url(path){
		return this.base_url + path
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
			await userHttp.updateAccessToken();
			return this._request(path, data, method)
		}else{
			console.log(response);
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

export default new BaseSeckillHttp();