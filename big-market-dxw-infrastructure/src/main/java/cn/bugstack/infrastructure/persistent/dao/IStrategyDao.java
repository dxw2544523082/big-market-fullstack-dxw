package cn.bugstack.infrastructure.persistent.dao;

import cn.bugstack.infrastructure.persistent.po.Strategy;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

/**
 * @author 丁晓武
 * @description 抽奖策略 DAO
 * @create
 */
@Mapper
public interface IStrategyDao {

    List<Strategy> queryStrategyList();

}
