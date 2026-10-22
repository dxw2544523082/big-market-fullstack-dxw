package cn.bugstack.infrastructure.persistent.dao;

import cn.bugstack.infrastructure.persistent.po.Award;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

/**
 * @author 丁晓武
 * @description 奖品表DAO
 * @create
 */
@Mapper
public interface IAwardDao {

    List<Award> queryAwardList();

}
