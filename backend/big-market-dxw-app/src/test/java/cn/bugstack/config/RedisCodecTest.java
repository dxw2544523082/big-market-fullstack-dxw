package cn.bugstack.config;

import cn.bugstack.domain.activity.model.entity.ActivityCountEntity;
import cn.bugstack.domain.strategy.model.valobj.RuleTreeVO;
import cn.bugstack.domain.strategy.model.valobj.RuleTreeNodeVO;
import io.netty.buffer.ByteBuf;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class RedisCodecTest {
    private Object roundTrip(Object value) throws Exception {
        RedisClientConfig.RedisCodec codec = new RedisClientConfig.RedisCodec();
        ByteBuf buffer = codec.getValueEncoder().encode(value);
        try {
            return codec.getValueDecoder().decode(buffer, null);
        } finally {
            buffer.release();
        }
    }

    @Test
    void restoresDomainObjectInsteadOfJSONObject() throws Exception {
        ActivityCountEntity input = ActivityCountEntity.builder()
                .activityCountId(11101L).totalCount(1000).dayCount(100).monthCount(1000).build();
        Object output = roundTrip(input);
        assertTrue(output instanceof ActivityCountEntity);
        assertEquals(input, output);
    }

    @Test
    void restoresNestedDomainObjectsInsideList() throws Exception {
        List<ActivityCountEntity> input = new ArrayList<>();
        input.add(ActivityCountEntity.builder().activityCountId(11101L).totalCount(1000).build());
        Object output = roundTrip(input);
        assertTrue(output instanceof List);
        assertTrue(((List<?>) output).get(0) instanceof ActivityCountEntity);
        assertEquals(input, output);
    }

    @Test
    void restoresRuleTreeWithTypedNestedMapAndChineseText() throws Exception {
        Map<String, RuleTreeNodeVO> nodes = new HashMap<>();
        nodes.put("rule_stock", RuleTreeNodeVO.builder().treeId("tree_luck_award")
                .ruleKey("rule_stock").ruleDesc("库存扣减规则").treeNodeLineVOList(new ArrayList<>()).build());
        RuleTreeVO input = RuleTreeVO.builder().treeId("tree_luck_award").treeName("规则树-兜底奖励")
                .treeDesc("规则树-兜底奖励").treeRootRuleNode("rule_stock").treeNodeMap(nodes).build();
        assertEquals(input, roundTrip(input));
    }

    @Test
    void handlesPrimitiveMapKeysAndQueueNumbers() throws Exception {
        assertEquals("demo", roundTrip("demo"));
        assertEquals(101, roundTrip(101));
    }
}
