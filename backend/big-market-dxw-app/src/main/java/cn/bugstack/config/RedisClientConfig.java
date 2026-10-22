package cn.bugstack.config;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONReader;
import com.alibaba.fastjson2.JSONWriter;
import com.alibaba.fastjson2.filter.Filter;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufAllocator;
import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.client.codec.BaseCodec;
import org.redisson.client.protocol.Decoder;
import org.redisson.client.protocol.Encoder;
import org.redisson.config.Config;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;

/**
 * Redis 客户端，使用 Redisson <a href="https://github.com/redisson/redisson">Redisson</a>
 *
 * @author Fuzhengwei bugstack.cn @小傅哥
 */
@Configuration
@EnableConfigurationProperties(RedisClientConfigProperties.class)
public class RedisClientConfig {

    @Bean("redissonClient")
    public RedissonClient redissonClient(ConfigurableApplicationContext applicationContext, RedisClientConfigProperties properties) {
        Config config = new Config();
        // 根据需要可以设定编解码器；https://github.com/redisson/redisson/wiki/4.-%E6%95%B0%E6%8D%AE%E5%BA%8F%E5%88%97%E5%8C%96
        config.setCodec(new RedisCodec());

        config.useSingleServer()
                .setAddress("redis://" + properties.getHost() + ":" + properties.getPort())
//                .setPassword(properties.getPassword())
                .setConnectionPoolSize(properties.getPoolSize())
                .setConnectionMinimumIdleSize(properties.getMinIdleSize())
                .setIdleConnectionTimeout(properties.getIdleTimeout())
                .setConnectTimeout(properties.getConnectTimeout())
                .setRetryAttempts(properties.getRetryAttempts())
                .setRetryInterval(properties.getRetryInterval())
                .setPingConnectionInterval(properties.getPingInterval())
                .setKeepAlive(properties.isKeepAlive())
        ;

        return Redisson.create(config);
    }

    static class RedisCodec extends BaseCodec {

        // Restore domain types written with @type, without globally enabling arbitrary AutoType.
        private static final Filter ALLOWED_TYPES = JSONReader.autoTypeFilter(
                "cn.bugstack.domain.",
                "java.util.ArrayList", "java.util.HashMap", "java.util.LinkedHashMap", "java.util.HashSet"
        );

        private final Encoder encoder = in -> {
            ByteBuf out = ByteBufAllocator.DEFAULT.buffer();
            try {
                // Typed fields already describe HashMap/ArrayList contents. Avoid redundant @type
                // metadata that breaks nested typed-map parsing in Fastjson2 2.0.28.
                out.writeBytes(JSON.toJSONBytes(in, JSONWriter.Feature.WriteClassName,
                        JSONWriter.Feature.NotWriteHashMapArrayListClassName));
                return out;
            } catch (Exception e) {
                out.release();
                throw new IOException(e);
            }
        };

        private final Decoder<Object> decoder = (buf, state) -> {
            byte[] bytes = new byte[buf.readableBytes()];
            buf.readBytes(bytes);
            return JSON.parseObject(bytes, Object.class, ALLOWED_TYPES);
        };

        @Override
        public Decoder<Object> getValueDecoder() {
            return decoder;
        }

        @Override
        public Encoder getValueEncoder() {
            return encoder;
        }

    }

}
